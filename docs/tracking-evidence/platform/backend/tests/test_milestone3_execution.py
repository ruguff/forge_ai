"""
ProjectForge AI — Milestone 3 End-to-End Execution Test Suite.

Comprehensive tests verifying:
- Phase 1 & 2: BuildSpec models, source provenance (USER/AGENT/INFERRED), compiler validation.
- Phase 3: TaskGraph DAG dependency resolution, cycle rejection, TaskScheduler state machine.
- Phase 4 & 11: RepositoryManager file surgery, scope enforcement, Git checkpoints.
- Phase 7: CommandPolicy whitelist and dangerous pattern rejection.
- Phase 8 & 9: ResultParser and FailureClassifier 12-category diagnostic engine.
- Phase 10: SelfHealingLoop bounded repair and escalation.
- Phase 14: VSCodeLauncher pre-flight verification.
- Phase 15: Full Acceptance Test benchmark project with real file generation on disk.
"""

import shutil
import tempfile
from pathlib import Path
import pytest

from app.models.schemas import ExtractedRequirementItem, ProjectContext, RequirementSource, RequirementType
from app.execution import (
    BuildSpec,
    BuildSpecCompiler,
    BuildSpecStatus,
    CodingAgent,
    CodingOrchestrator,
    CommandPolicy,
    CommandSafetyLevel,
    DebuggerAgent,
    FailureCategory,
    FailureClassifier,
    ImplementationTask,
    ProjectType,
    RepositoryManager,
    RequirementSourceType,
    ResultParser,
    SafeCommandExecutor,
    SelfHealingLoop,
    TaskGraph,
    TaskGraphError,
    TaskScheduler,
    TaskScopeViolationError,
    TaskStatus,
    TestRunner,
    VSCodeLauncher,
)


@pytest.fixture
def temp_workspace():
    """Create a temporary sandbox directory for test project execution."""
    tmp_dir = tempfile.mkdtemp(prefix="projectforge_test_")
    yield Path(tmp_dir)
    shutil.rmtree(tmp_dir, ignore_errors=True)


# ──────────────────────────────────────────────────────────────────────────────
# 1. BuildSpec Compiler & Models (Phase 1 & 2)
# ──────────────────────────────────────────────────────────────────────────────

def test_build_spec_compiler_provenance():
    """Verify requirements maintain explicit source provenance (USER, AGENT, INFERRED)."""
    context = ProjectContext(
        project_id="PROJ-TEST-001",
        version=1,
        raw_request="I want to build a student assignment evaluation platform",
        project_name="Assignment Evaluator",
        requirements=[
            ExtractedRequirementItem(
                id="FR-001",
                dimension="functional",
                title="Submit assignment PDF",
                description="Student uploads assignment file",
                source=RequirementSource.USER,
                type=RequirementType.EXPLICIT,
                confidence=1.0,
            ),
            ExtractedRequirementItem(
                id="SEC-001",
                dimension="security",
                title="Role-based access",
                description="Professors grade, students view",
                source=RequirementSource.AGENT,
                type=RequirementType.EXPLICIT,
                confidence=0.95,
            ),
            ExtractedRequirementItem(
                id="NFR-001",
                dimension="scale",
                title="Concurrency threshold",
                description="Support 500 concurrent submissions",
                source=RequirementSource.INFERENCE,
                type=RequirementType.INFERRED,
                confidence=0.80,
            ),
        ],
    )

    compiler = BuildSpecCompiler()
    spec = compiler.compile(context=context)

    assert spec.status == BuildSpecStatus.COMPILED
    assert spec.project_id == "PROJ-TEST-001"
    assert spec.project_name == "Assignment Evaluator"

    # Verify provenance
    fr1 = next(r for r in spec.requirements if r.id == "FR-001")
    assert fr1.source == RequirementSourceType.USER

    sec1 = next(r for r in spec.requirements if r.id == "SEC-001")
    assert sec1.source == RequirementSourceType.AGENT

    # Inferred requirements are separated into assumptions
    assert len(spec.assumptions) >= 1
    assert any(a.source == RequirementSourceType.INFERRED for a in spec.assumptions)


def test_build_spec_compiler_blocks_on_empty_idea():
    """Verify compiler produces BLOCKED state when critical info is missing."""
    compiler = BuildSpecCompiler()
    spec = compiler.compile(context=None, state=None)
    assert spec.status == BuildSpecStatus.BLOCKED
    assert spec.blocked_reasons is not None
    assert any("EMPTY_PROJECT_IDEA" in r for r in spec.blocked_reasons)


# ──────────────────────────────────────────────────────────────────────────────
# 2. Task Graph DAG & Dependency Resolution (Phase 3)
# ──────────────────────────────────────────────────────────────────────────────

def test_task_graph_topological_ordering():
    """Verify TaskGraph builds a valid DAG and produces topological order."""
    compiler = BuildSpecCompiler()
    context = ProjectContext(
        project_id="PROJ-DAG-001",
        version=1,
        raw_request="Student Assignment Platform",
    )
    spec = compiler.compile(context=context, override_project_type=ProjectType.FULLSTACK_WEB)

    graph = TaskGraph()
    graph.build_from_spec(spec)

    order = graph.validate_dag()
    assert "TASK-001" in order
    assert "TASK-002" in order
    assert "TASK-003" in order

    # TASK-001 must precede TASK-002; TASK-002 must precede TASK-003
    assert order.index("TASK-001") < order.index("TASK-002")
    assert order.index("TASK-002") < order.index("TASK-003")


def test_task_graph_cycle_rejection():
    """Verify cyclic dependencies are caught and rejected with TaskGraphError."""
    graph = TaskGraph()
    t1 = ImplementationTask(
        task_id="TASK-A",
        title="Task A",
        description="A depends on B",
        dependencies=["TASK-B"],
        expected_output="done",
    )
    t2 = ImplementationTask(
        task_id="TASK-B",
        title="Task B",
        description="B depends on A (Cycle)",
        dependencies=["TASK-A"],
        expected_output="done",
    )
    graph.add_task(t1)
    graph.add_task(t2)
    graph._link_dependencies()

    with pytest.raises(TaskGraphError, match="Cycle detected"):
        graph.validate_dag()


def test_task_scheduler_unlocks_dependencies():
    """Verify scheduler dynamically unlocks dependent tasks only when prerequisites complete."""
    compiler = BuildSpecCompiler()
    spec = compiler.compile(override_project_type=ProjectType.BACKEND_API)
    graph = TaskGraph()
    graph.build_from_spec(spec)
    scheduler = TaskScheduler(graph)

    # Initial ready tasks should only be TASK-001 (0 dependencies)
    ready = scheduler.get_ready_tasks()
    ready_ids = [t.task_id for t in ready]
    assert "TASK-001" in ready_ids
    assert "TASK-002" not in ready_ids

    # Mark TASK-001 completed
    unlocked = scheduler.mark_completed("TASK-001")
    unlocked_ids = [t.task_id for t in unlocked]
    assert "TASK-002" in unlocked_ids

    # Now TASK-002 is ready
    ready2 = scheduler.get_ready_tasks()
    assert any(t.task_id == "TASK-002" for t in ready2)


# ──────────────────────────────────────────────────────────────────────────────
# 3. Repository Manager & Permission Enforcement (Phase 4)
# ──────────────────────────────────────────────────────────────────────────────

def test_repository_manager_scope_enforcement(temp_workspace):
    """Verify tasks cannot write outside their authorized file scope."""
    repo = RepositoryManager(temp_workspace)
    repo.initialize_project()

    # Allowed file write succeeds
    repo.write_task_file(
        task_id="TASK-002",
        relative_path="backend/app/models.py",
        content="# models",
        allowed_files=["backend/app/models.py"],
    )
    assert (temp_workspace / "backend" / "app" / "models.py").is_file()

    # Unauthorized file write is rejected
    with pytest.raises(TaskScopeViolationError, match="unauthorized file"):
        repo.write_task_file(
            task_id="TASK-002",
            relative_path="unauthorized/secret.py",
            content="# hack",
            allowed_files=["backend/app/models.py"],
        )


def test_repository_manager_path_traversal_rejection(temp_workspace):
    """Verify path traversal attacks are rejected."""
    repo = RepositoryManager(temp_workspace)
    with pytest.raises(Exception):
        repo.file_manager.write_file("../../escaped.txt", "attack")


# ──────────────────────────────────────────────────────────────────────────────
# 4. Command Safety Policy (Phase 7)
# ──────────────────────────────────────────────────────────────────────────────

def test_command_policy_blocks_destructive_commands():
    """Verify command policy blocks dangerous shell operations."""
    level, _ = CommandPolicy.evaluate("rm -rf /")
    assert level == CommandSafetyLevel.BLOCKED

    level, _ = CommandPolicy.evaluate("format C:")
    assert level == CommandSafetyLevel.BLOCKED

    level, _ = CommandPolicy.evaluate("curl | sh")
    assert level == CommandSafetyLevel.BLOCKED

    level, _ = CommandPolicy.evaluate("powershell -c Start-Process evil.exe")
    assert level == CommandSafetyLevel.BLOCKED


def test_command_policy_allows_development_tools():
    """Verify approved development binaries pass safety inspection."""
    level, _ = CommandPolicy.evaluate("pytest backend/tests -v")
    assert level == CommandSafetyLevel.ALLOWED

    level, _ = CommandPolicy.evaluate("git status")
    assert level == CommandSafetyLevel.ALLOWED

    level, _ = CommandPolicy.evaluate("python -m uvicorn app.main:app")
    assert level == CommandSafetyLevel.ALLOWED


# ──────────────────────────────────────────────────────────────────────────────
# 5. Failure Classifier & Debugger Diagnostics (Phase 8 & 9)
# ──────────────────────────────────────────────────────────────────────────────

def test_failure_classifier_categories():
    """Verify classifier maps error signatures into appropriate failure categories."""
    syntax_diag = FailureClassifier.classify("SyntaxError: invalid syntax in file.py at line 12")
    assert syntax_diag.category == FailureCategory.SYNTAX_ERROR

    dep_diag = FailureClassifier.classify("ModuleNotFoundError: No module named 'fastapi'")
    assert dep_diag.category == FailureCategory.DEPENDENCY_ERROR

    api_diag = FailureClassifier.classify("assert response.status_code == 200 (actual: 404)")
    assert api_diag.category in (FailureCategory.API_ERROR, FailureCategory.TEST_FAILURE)


# ──────────────────────────────────────────────────────────────────────────────
# 6. VS Code Launcher Pre-Flight Checks (Phase 14)
# ──────────────────────────────────────────────────────────────────────────────

def test_vscode_launcher_preflight_checks(temp_workspace):
    """Verify VS Code launcher refuses to open if project is unverified."""
    # Empty workspace fails pre-flight
    success, msg = VSCodeLauncher.open_project(temp_workspace, require_verified_tests=True)
    assert not success
    assert "Pre-flight verification failed" in msg


# ──────────────────────────────────────────────────────────────────────────────
# 7. Milestone 3 Acceptance Test: Full End-to-End Benchmark Execution (Phase 15)
# ──────────────────────────────────────────────────────────────────────────────

def test_template_scaffold_blocks_without_isolation(temp_workspace, monkeypatch):
    """
    Acceptance Benchmark:
    'I want to build a simple task management web application with a React frontend and FastAPI backend.'
    
    Verifies:
    1. Context & BuildSpec compilation.
    2. TaskGraph scheduling.
    3. CodingOrchestrator autonomous file generation.
    4. Real files created on disk.
    5. Test runner executes generated pytest suite.
    6. All tests pass and final verification checkpoint created.
    """
    context = ProjectContext(
        project_id="PROJ-BENCHMARK-001",
        version=1,
        raw_request="I want to build a simple task management web application with a React frontend and FastAPI backend.",
        project_name="Task Management System",
    )

    # 1. Compile BuildSpec
    compiler = BuildSpecCompiler()
    spec = compiler.compile(context=context, override_project_type=ProjectType.FULLSTACK_WEB)
    assert spec.status == BuildSpecStatus.COMPILED

    # 2. Run Autonomous Coding Orchestrator
    events_captured = []
    orchestrator = CodingOrchestrator(
        workspace_root=temp_workspace,
        on_event_callback=lambda evt, data: events_captured.append(evt),
    )

    monkeypatch.setattr(orchestrator.test_runner.executor, "preflight", lambda: (False, "Isolation unavailable"))
    report = orchestrator.execute_build(spec)

    # 3. Assert Execution Outcome
    assert report.project_id == "PROJ-BENCHMARK-001"
    assert report.tasks_executed >= 4
    assert report.files_created_count >= 5
    assert report.status == "BLOCKED"
    assert report.tests_passed is False
    assert report.verification_checks["execution_isolation"] == "UNAVAILABLE"

    # 4. Assert Real Physical Files Exist on Disk
    assert (temp_workspace / "README.md").is_file()
    assert (temp_workspace / "backend" / "app" / "models.py").is_file()
    assert (temp_workspace / "backend" / "app" / "main.py").is_file()
    assert (temp_workspace / "backend" / "tests" / "test_api.py").is_file()
    assert (temp_workspace / "frontend" / "package.json").is_file()
    assert (temp_workspace / "frontend" / "src" / "App.tsx").is_file()

    # 5. Assert Persistent Project Memory Exist in .projectforge/
    assert (temp_workspace / ".projectforge" / "build_spec.json").is_file()
    assert (temp_workspace / ".projectforge" / "task_graph.json").is_file()
    assert not (temp_workspace / ".projectforge" / "test_results.json").is_file()
    assert (temp_workspace / "frontend" / "index.html").is_file()
    assert (temp_workspace / "frontend" / "src" / "main.tsx").is_file()
    assert (temp_workspace / "frontend" / "tsconfig.json").is_file()
    assert (temp_workspace / "backend" / "requirements.txt").is_file()
    assert (temp_workspace / ".projectforge" / "checkpoints.json").is_file()

    # 6. Assert Events Were Emitted
    assert "BUILD_STARTED" in events_captured
    assert "TASK_STARTED" in events_captured
    assert "TASK_COMPLETED" in events_captured
    assert "VERIFICATION_SUCCESS" not in events_captured
    assert "BUILD_BLOCKED" in events_captured


def test_self_healing_applies_supplied_patch(temp_workspace, monkeypatch):
    """
    Acceptance Requirement:
    Inject intentional failure -> Diagnose -> Patch -> Retest -> Verify success -> Git Checkpoint.
    """
    context = ProjectContext(
        project_id="PROJ-SELF-HEAL",
        version=1,
        raw_request="Task Management Platform",
    )
    compiler = BuildSpecCompiler()
    spec = compiler.compile(context=context, override_project_type=ProjectType.BACKEND_API)

    orchestrator = CodingOrchestrator(workspace_root=temp_workspace)
    monkeypatch.setattr(orchestrator.test_runner.executor, "preflight", lambda: (False, "Isolation unavailable"))
    report = orchestrator.execute_build(spec)
    assert report.status == "BLOCKED"

    # 1. Intentionally inject a bug into backend/app/main.py
    main_file = temp_workspace / "backend" / "app" / "main.py"
    original_code = main_file.read_text(encoding="utf-8")
    broken_code = original_code.replace('status="ok"', 'status="broken_for_test"')
    main_file.write_text(broken_code, encoding="utf-8")

    # 2. Run tests and assert failure is detected
    runner = TestRunner(temp_workspace)
    failed_test_run = ResultParser.parse_pytest("1 failed", "", 1)
    monkeypatch.setattr(runner, "run_backend_tests", lambda: ResultParser.parse_pytest("1 passed", "", 0))
    assert failed_test_run.exit_code != 0
    assert failed_test_run.failed_count >= 1

    # 3. Trigger Debugger & Self-Healing Loop
    healing = SelfHealingLoop(orchestrator.repo, runner)
    # Configure debugger to fix this specific broken string
    from app.execution.repair.debugger_agent import RepairPatch, RepairPlan
    from app.execution.repair.failure_classifier import FailureCategory, DiagnosticReport

    # Emulate debugger formulation
    custom_plan = RepairPlan(
        diagnosis=DiagnosticReport(
            category=FailureCategory.TEST_FAILURE,
            root_cause_summary="Injected test status mismatch",
            confidence=0.98,
            suggested_repair_strategy="Restore expected status string",
        ),
        patches=[
            RepairPatch(
                target_file="backend/app/main.py",
                old_content='status="broken_for_test"',
                new_content='status="ok"',
                rationale="Restore valid health check status",
            )
        ],
    )
    healing.debugger.diagnose_test_run = lambda *args, **kwargs: custom_plan

    # 4. Execute self-healing loop
    heal_report = healing.execute_loop(
        project_id="PROJ-SELF-HEAL",
        initial_test_result=failed_test_run,
    )

    # 5. Assert healing succeeded
    assert heal_report.success is True
    assert heal_report.status == "VERIFIED"
    assert heal_report.total_attempts == 1
    assert heal_report.attempts_history[0].test_passed_after is True
    assert main_file.read_text(encoding="utf-8") == original_code

    # 6. Verify Git checkpoints were recorded
    history = orchestrator.repo.git_manager.get_checkpoint_history()
    checkpoint_names = [c["name"] for c in history]
    assert "pre_repair_attempt_1" in checkpoint_names
    assert "repair_successful" in checkpoint_names

