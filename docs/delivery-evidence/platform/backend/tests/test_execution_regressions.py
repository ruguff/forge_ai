import asyncio
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock
import httpx
import pytest
from app.main import app
from app.api import endpoints
from app.api.persistence import ProjectPersistence
from app.models.schemas import (ProjectContext, ProjectState, ProjectStatus,
    ExtractedRequirementItem, RequirementSource, RequirementType)
from app.agents.understanding_service import generate_heuristic_understanding
from app.execution import BuildSpecCompiler, CodingOrchestrator, ProjectType, ResultParser, TaskGraph
from app.execution.agent.coding_agent import CodingAgent
from app.execution.agent.tools import AgentToolContext
from app.execution.repository.repository_manager import RepositoryManager
from app.execution.sandbox.executor import CommandExecutionBlockedError, SafeCommandExecutor, ExecutionResult
from app.execution.verification import source_digest


@pytest.mark.asyncio
async def test_unknown_project_is_not_created_implicitly():
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        for route in ("understand", "analyze", "build", "open-editor"):
            response = await client.post(f"/api/projects/PROJ-NONEXISTENT/{route}")
            assert response.status_code == 404


@pytest.mark.asyncio
async def test_clarification_resolves_requirement_and_prevents_duplicate_answer():
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        created = await client.post("/api/projects", json={"idea": "Detect road changes in satellite imagery"})
        pid = created.json()["project_id"]
        result = (await client.post(f"/api/projects/{pid}/understand")).json()
        question = result["clarification"]
        assert question is not None
        answer = {"question_id": question["question_id"], "answer": question["possible_options"][0]}
        clarified = (await client.post(f"/api/projects/{pid}/clarify", json=answer)).json()
        context = clarified["context"]
        assert not any(u["id"] == question["unknown_item_id"] for u in context["unknowns"])
        assert any(r["id"] == question["unknown_item_id"] and r["description"] == answer["answer"] for r in context["requirements"])
        assert (await client.post(f"/api/projects/{pid}/clarify", json=answer)).status_code == 409


@pytest.mark.asyncio
async def test_analysis_without_model_key_does_not_emit_completion():
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        pid = (await client.post("/api/projects", json={"idea": "A simple list website"})).json()["project_id"]
        await client.post(f"/api/projects/{pid}/understand")
        response = await client.post(f"/api/projects/{pid}/analyze")
        assert response.status_code == 503
        kinds = [payload["type"] for _, payload in endpoints._PERSISTENCE.events_after(pid, 0)]
        assert "PIPELINE_BLOCKED" in kinds
        assert "AGENT_COMPLETED" not in kinds
        assert "BLUEPRINT_GENERATED" not in kinds


def test_persistence_and_event_readers_are_independent(tmp_path):
    store = ProjectPersistence(tmp_path / "state.sqlite3")
    state = ProjectState(project_id="PROJ-PERSIST", status=ProjectStatus.INTAKE, raw_idea="Website", intake_qa={})
    context = ProjectContext(project_id=state.project_id, raw_request=state.raw_idea)
    store.save(state.project_id, state, context)
    first = store.append_event(state.project_id, {"type": "PROJECT_CREATED"})
    assert store.events_after(state.project_id, 0) == store.events_after(state.project_id, 0)
    assert len(store.events_after(state.project_id, first)) == 0
    reloaded = ProjectPersistence(store.path)
    assert reloaded.load_all()[0]["context"]["raw_request"] == "Website"
    context.version += 1
    store.save(state.project_id, state, context)
    with store.connect() as db:
        assert db.execute("SELECT COUNT(*) FROM history").fetchone()[0] == 2


def test_offline_suggestions_do_not_claim_user_provenance():
    result = generate_heuristic_understanding("Build a bakery website")
    assert all(r.source != RequirementSource.USER for r in result.functional_requirements)
    assert all(r.type != RequirementType.EXPLICIT for r in result.functional_requirements)
    assert any("HEURISTIC" in evidence for evidence in result.evidence)


def test_no_host_execution_when_container_is_missing(tmp_path, monkeypatch):
    executor = SafeCommandExecutor(tmp_path)
    executor.docker = None
    popen = Mock()
    monkeypatch.setattr("subprocess.Popen", popen)
    with pytest.raises(CommandExecutionBlockedError):
        executor.execute("python -m pytest")
    popen.assert_not_called()


def test_no_tests_cannot_count_as_success():
    assert not ResultParser.parse_pytest("no tests ran", "", 0).is_success


def test_blocked_spec_does_not_generate_source(tmp_path):
    spec = BuildSpecCompiler().compile()
    report = CodingOrchestrator(tmp_path).execute_build(spec)
    assert report.status == "BLOCKED"
    assert report.tasks_executed == 0
    assert not (tmp_path / "backend/app/main.py").exists()


def test_explicit_resume_reuses_source_but_rechecks_sandbox(tmp_path, monkeypatch):
    context = ProjectContext(project_id='PROJ-RESUME', raw_request='Simple task website')
    spec = BuildSpecCompiler().compile(context)
    orchestrator = CodingOrchestrator(tmp_path)
    preflight = Mock(return_value=(False, 'Docker unavailable'))
    monkeypatch.setattr(orchestrator.test_runner.executor, 'preflight', preflight)
    first = orchestrator.execute_build(spec)
    assert first.tasks_executed > 0
    assert first.status == 'BLOCKED'
    generate = Mock(side_effect=AssertionError('Completed files must not regenerate'))
    monkeypatch.setattr(orchestrator.coding_agent, 'execute_task', generate)
    resumed = orchestrator.execute_build(spec, resume=True)
    assert resumed.tasks_executed == 0
    assert resumed.status == 'BLOCKED'
    assert preflight.call_count == 2
    generate.assert_not_called()


def test_failed_frontend_prevents_verified_status(tmp_path, monkeypatch):
    context = ProjectContext(project_id="PROJ-FRONTEND", raw_request="Simple task website")
    spec = BuildSpecCompiler().compile(context)
    spec.acceptance_checks = [{"method": "GET", "path": "/api/health", "status": 200}]
    spec.browser_checks = [{"steps": [{"action": "visible", "selector": "h1"}]}]
    orchestrator = CodingOrchestrator(tmp_path)
    runner = orchestrator.test_runner
    passed = ResultParser.parse_pytest("2 passed", "", 0)
    monkeypatch.setattr(runner.executor, "preflight", lambda: (True, "isolated test double"))
    monkeypatch.setattr(runner, "run_backend_tests", lambda: passed)
    monkeypatch.setattr(runner, "run_acceptance", lambda checks: passed)
    monkeypatch.setattr(runner, "run_browser_checks", lambda checks: passed)
    monkeypatch.setattr(runner, "run_frontend_build", lambda: ExecutionResult(command="build", exit_code=1, stdout="", stderr="Compile error", duration_ms=1))
    report = orchestrator.execute_build(spec)
    assert report.status == "REQUIRES_HUMAN"
    assert report.verification_checks["frontend_build"] == "FAILED"


def test_identity_authority_failure_prevents_verified_status(tmp_path,monkeypatch):
    from app.execution.spec.catalogue_example import example_spec
    from app.execution.spec.identity_contract import IdentityContract
    from app.execution.agent.identity import prepare_spec
    spec=example_spec();spec.identity_contract=IdentityContract();spec.tech_stack.auth_provider='session';spec=prepare_spec(spec)
    spec.acceptance_checks=[{'method':'GET','path':'/api/store','status':200}]
    spec.browser_checks=[{'steps':[{'action':'visible','selector':'h1'}]}]
    orchestrator=CodingOrchestrator(tmp_path);runner=orchestrator.test_runner
    passed=ResultParser.parse_pytest('1 passed','',0)
    monkeypatch.setattr(runner.executor,'preflight',lambda:(True,'isolated test double'))
    monkeypatch.setattr(runner,'run_backend_tests',lambda:passed)
    monkeypatch.setattr(runner,'run_acceptance',lambda checks:passed)
    monkeypatch.setattr(runner,'run_browser_checks',lambda checks:passed)
    monkeypatch.setattr(runner,'run_frontend_build',lambda:ExecutionResult(command='build',exit_code=0,stdout='',stderr='',duration_ms=1))
    monkeypatch.setattr(runner,'run_identity_checks',lambda:ResultParser.parse_pytest('1 failed','',1))
    report=orchestrator.execute_build(spec)
    assert report.tests_passed is True
    assert report.status=='REQUIRES_HUMAN'
    assert report.verification_checks['identity_authority']=='FAILED'


def test_order_integrity_failure_prevents_verified_status(tmp_path,monkeypatch):
    from app.execution.spec.catalogue_example import example_spec
    from app.execution.spec.identity_contract import IdentityContract
    from app.execution.spec.order_contract import OrderContract
    from app.execution.agent.orders import prepare_spec
    spec=example_spec()
    spec.identity_contract=IdentityContract(public_origin='http://127.0.0.1:3001',allow_local_http=True)
    spec.tech_stack.auth_provider='session'
    spec.order_contract=OrderContract(tax_basis_points=500,shipping_minor=100,discount_basis_points=0,policy_label='Synthetic test rules')
    spec=prepare_spec(spec)
    spec.acceptance_checks=[{'method':'GET','path':'/api/store','status':200}]
    spec.browser_checks=[{'name':'catalogue','requirements':['CAT-001'],'steps':[{'action':'text','selector':'h1','value':'Fieldwork'}]}]
    orchestrator=CodingOrchestrator(tmp_path);runner=orchestrator.test_runner
    passed=ResultParser.parse_pytest('1 passed','',0)
    monkeypatch.setattr(runner.executor,'preflight',lambda:(True,'isolated test double'))
    monkeypatch.setattr(runner,'run_backend_tests',lambda:passed)
    monkeypatch.setattr(runner,'run_acceptance',lambda checks:passed)
    monkeypatch.setattr(runner,'run_browser_checks',lambda checks:passed)
    monkeypatch.setattr(runner,'run_frontend_build',lambda:ExecutionResult(command='build',exit_code=0,stdout='',stderr='',duration_ms=1))
    monkeypatch.setattr(runner,'run_identity_checks',lambda:passed)
    monkeypatch.setattr(runner,'run_order_checks',lambda:ResultParser.parse_pytest('1 failed','',1))
    monkeypatch.setattr(runner,'run_order_browser_checks',lambda:passed)
    report=orchestrator.execute_build(spec)
    assert report.tests_passed is True
    assert report.status=='REQUIRES_HUMAN'
    assert report.verification_checks['identity_authority']=='PASSED'
    assert report.verification_checks['order_integrity']=='FAILED'
    assert report.verification_checks['order_browser_journey']=='PASSED'


def test_fingerprint_changes_with_source(tmp_path):
    source = tmp_path / "app.py"
    source.write_text("first")
    before = source_digest(tmp_path)
    source.write_text("second")
    assert source_digest(tmp_path) != before


def test_model_coder_obeys_scope_and_uses_model_content(tmp_path):
    context = ProjectContext(project_id="PROJ-CODER", raw_request="Website")
    spec = BuildSpecCompiler().compile(context)
    spec.generation_mode = "MODEL"
    from app.execution.tasks.task_models import ImplementationTask
    task = ImplementationTask(task_id="FILE-001", title="Source", description="Source", expected_output="Source",
                              files_to_create=["backend/app/main.py"])
    repo = RepositoryManager(tmp_path)
    tools = AgentToolContext(repo, task.task_id, task.files_to_create)
    model = SimpleNamespace(generate_sync=lambda prompt: json.dumps({"files": {"backend/app/main.py": "VALUE = 42\n"}}))
    result = CodingAgent(model_client=model).execute_task(task, spec, tools)
    assert repo.read_file("backend/app/main.py") == "VALUE = 42\n"
    assert result.files_created == task.files_to_create
    model.generate_sync = lambda prompt: json.dumps({"files": {"../../escape.py": "bad"}})
    with pytest.raises(ValueError):
        CodingAgent(model_client=model).execute_task(task, spec, tools)


@pytest.mark.asyncio
async def test_real_specialist_harnesses_run_in_dependency_order():
    from app.agents.pipeline import run_specialists
    from tests.test_agents import (_make_valid_product_json, _make_valid_aiml_no_ai_json,
        _make_valid_engineering_json, _make_valid_ux_json, _make_valid_security_json, _make_valid_qa_json)
    fixtures = {
        "ProductSpecification": _make_valid_product_json(),
        "AIArchitectureSpecification": _make_valid_aiml_no_ai_json(),
        "EngineeringSpecification": _make_valid_engineering_json(),
        "UXSpecification": _make_valid_ux_json(),
        "SecurityReport": _make_valid_security_json(),
        "QASpecification": _make_valid_qa_json(),
    }
    ux = json.loads(fixtures["UXSpecification"])
    ux["primary_user_journey"] = ["Open dashboard", "Submit task", "Read saved task"]
    fixtures["UXSpecification"] = json.dumps(ux)
    calls = []
    async def generate(prompt):
        for name, output in fixtures.items():
            if f'"title": "{name}"' in prompt:
                calls.append(name)
                if name == "EngineeringSpecification":
                    assert '"product_spec"' in prompt and '"ai_spec"' in prompt
                if name == "QASpecification":
                    assert '"security_report"' in prompt
                assert '"project_context"' in prompt
                return output
        raise AssertionError("Unrecognized agent prompt")
    state = ProjectState(project_id="PROJ-REAL-TEST", status=ProjectStatus.INTAKE, raw_idea="Task website", intake_qa={})
    context = ProjectContext(project_id=state.project_id, raw_request=state.raw_idea)
    events = []
    async def emit(kind, role=None, message="", data=None):
        events.append(kind)
    await run_specialists(state, context, SimpleNamespace(generate=generate), emit, lambda: None)
    assert calls[:3] == ["ProductSpecification", "AIArchitectureSpecification", "EngineeringSpecification"]
    assert calls[-1] == "QASpecification"
    assert len(calls) == 6
    assert events.count("AGENT_COMPLETED") == 6
    assert "CONFLICT_DETECTED" not in events
    assert state.final_blueprint_markdown


def test_model_spec_validation_rejects_incomplete_site_and_bad_paths():
    from app.execution.spec.model_compiler import validate_spec
    context = ProjectContext(project_id="PROJ-SPEC", raw_request="Simple website")
    spec = BuildSpecCompiler().compile(context)
    errors = validate_spec(spec, context)
    assert any("Missing startup files" in error for error in errors)
    spec.files_to_create[0].file_path = "../../escape.py"
    assert any("Unsafe" in error for error in validate_spec(spec, context))


def test_repair_cannot_weaken_tests_or_contracts(tmp_path, monkeypatch):
    from app.execution.repair.self_healing_loop import SelfHealingLoop
    from app.execution.sandbox.test_runner import TestRunner
    loop = SelfHealingLoop(RepositoryManager(tmp_path), TestRunner(tmp_path))
    assert not loop._repair_allowed("backend/tests/test_api.py")
    assert not loop._repair_allowed(".projectforge/test_acceptance.py")
    assert not loop._repair_allowed("../../outside.py")
    assert loop._repair_allowed("backend/app/main.py")
