"""Project lifecycle, real agents, durable snapshots and broadcast/replay SSE."""
from __future__ import annotations
import asyncio
import json
import logging
import re
import uuid
from pathlib import Path
from typing import Literal
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from app.api.persistence import ProjectPersistence
from app.agents.model_client import GeminiModelClient, ModelUnavailableError, ModelBudgetExceeded
from app.agents.pipeline import run_specialists
from app.agents.requirement_engine import RequirementEngine
from app.agents.understanding_service import execute_understanding
from app.config import get_settings
from app.models.schemas import (ProjectState, ProjectContext, ProjectStatus,
    DecisionRecord, ExtractedRequirementItem, RequirementSource, RequirementType)
from app.execution import BuildSpec, BuildSpecCompiler, CodingOrchestrator, VSCodeLauncher

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/projects", tags=["projects"])
_PROJECT_STORE = {}
_CONTEXT_STORE = {}
_BUILD_SPEC_STORE = {}
_EVENT_QUEUES = {}  # Bounded compatibility buffer; streaming uses persisted events.
_SIGNALS = {}
_RUN_TASKS = {}
_ACTIVE = set()
_PERSISTENCE = ProjectPersistence()
WORKSPACES = Path(__file__).resolve().parents[2] / "generated_projects"


def save_project(project_id):
    _PERSISTENCE.save(project_id, _PROJECT_STORE[project_id], _CONTEXT_STORE[project_id],
                      _BUILD_SPEC_STORE.get(project_id))


for _snapshot in _PERSISTENCE.load_all():
    _state = ProjectState.model_validate(_snapshot["state"])
    _context = ProjectContext.model_validate(_snapshot["context"])
    if _context.execution_state in {"ANALYZING", "UNDERSTANDING", "BUILDING"}:
        _context.execution_state = "INTERRUPTED"
        _state.status = ProjectStatus.AWAITING_HUMAN_REVIEW
    _PROJECT_STORE[_state.project_id] = _state
    _CONTEXT_STORE[_state.project_id] = _context
    if _snapshot["spec"]:
        _BUILD_SPEC_STORE[_state.project_id] = BuildSpec.model_validate(_snapshot["spec"])


def get_project(project_id):
    if not re.fullmatch(r"PROJ-[A-Z0-9-]{1,64}", project_id):
        raise HTTPException(400, "Invalid project identifier")
    if project_id not in _PROJECT_STORE:
        raise HTTPException(404, "Project not found")
    return _PROJECT_STORE[project_id], _CONTEXT_STORE[project_id]


def invalidate(project_id):
    state, context = get_project(project_id)
    for field in ("product_spec", "ai_spec", "engineering_spec", "ux_spec", "security_report", "qa_spec"):
        setattr(state, field, None)
    state.detected_conflicts = []
    state.final_blueprint_markdown = None
    context.agent_outputs = {}
    context.conflicts = []
    context.architecture = None
    context.build_spec = None
    _BUILD_SPEC_STORE.pop(project_id, None)


async def emit_event(project_id, event_type, agent_id=None, message="", data=None):
    payload = {"type": event_type, "agent_id": agent_id, "message": message, "data": data or {}}
    sequence = _PERSISTENCE.append_event(project_id, payload)
    queue = _EVENT_QUEUES.setdefault(project_id, asyncio.Queue(maxsize=256))
    if queue.full():
        queue.get_nowait()
    queue.put_nowait(json.dumps(payload))
    signal = _SIGNALS.setdefault(project_id, asyncio.Condition())
    async with signal:
        signal.notify_all()
    if project_id in _PROJECT_STORE:
        save_project(project_id)
    return sequence


class CreateProjectRequest(BaseModel):
    idea: str = Field(min_length=1, max_length=20000)
    mode: Literal["AUTONOMOUS", "GUIDED"] = "AUTONOMOUS"


class ClarifyAnswerRequest(BaseModel):
    question_id: str
    answer: str = Field(min_length=1, max_length=10000)


class ApprovalRequest(BaseModel):
    version: int


class ConflictResolutionRequest(BaseModel):
    decision: str = Field(min_length=1, max_length=10000)


@router.post("")
async def create_project(req: CreateProjectRequest):
    if not req.idea.strip():
        raise HTTPException(422, "Idea must not be blank")
    project_id = f"PROJ-{uuid.uuid4().hex[:12].upper()}"
    _PROJECT_STORE[project_id] = ProjectState(project_id=project_id, status=ProjectStatus.INTAKE,
                                               raw_idea=req.idea, intake_qa={})
    _CONTEXT_STORE[project_id] = ProjectContext(project_id=project_id, raw_request=req.idea, mode=req.mode)
    await emit_event(project_id, "PROJECT_CREATED", message="Project saved.", data={"mode": req.mode})
    return {"project_id": project_id, "status": "created", "version": 1}


@router.post("/{project_id}/understand")
async def understand_project(project_id: str):
    state, context = get_project(project_id)
    if project_id in _ACTIVE:
        raise HTTPException(409, "A project operation is already running")
    _ACTIVE.add(project_id)
    try:
        invalidate(project_id)
        context.version += 1
        state.revision = context.version
        context.execution_state = "UNDERSTANDING"
        await emit_event(project_id, "UNDERSTANDING_STARTED", "project_understanding", "Extracting requirements.")
        output = await execute_understanding(context.raw_request)
        context.project_name = output.project_name
        context.problem_statement = output.problem.description
        context.goals = [output.goal.description]
        context.target_users = [u.description for u in output.target_users]
        context.user_journeys = [j.description for j in output.user_journeys]
        context.requirements = [output.problem, output.goal, *output.functional_requirements,
            *output.non_functional_requirements, *output.expected_outputs, *output.technology_preferences,
            *output.non_goals, *output.risks]
        context.assumptions = output.assumptions
        context.unknowns = output.unknowns
        context.constraints = output.constraints
        result = RequirementEngine().evaluate_requirements(output)
        context.clarification_questions = result.clarification_questions
        clarification = next(iter(context.clarification_questions), None)
        context.execution_state = "CLARIFICATION_REQUIRED" if clarification else "REQUIREMENTS_VALIDATED"
        await emit_event(project_id, "UNDERSTANDING_COMPLETED", "project_understanding", "Requirement extraction completed.",
                         {"requirements_count": len(context.requirements), "evidence": output.evidence})
        await emit_event(project_id, context.execution_state, "requirement_engine",
                         clarification.question if clarification else "Ready for specialist analysis.",
                         clarification.model_dump(mode="json") if clarification else {})
        return {"project_id": project_id, "execution_state": context.execution_state,
                "context": context.model_dump(mode="json"),
                "clarification": clarification.model_dump(mode="json") if clarification else None,
                "next_clarification": clarification.model_dump(mode="json") if clarification else None}
    except Exception:
        context.execution_state = "FAILED"
        await emit_event(project_id, "UNDERSTANDING_FAILED", message="Requirement extraction failed.")
        raise
    finally:
        _ACTIVE.discard(project_id)


@router.post("/{project_id}/clarify")
async def clarify_question(project_id: str, req: ClarifyAnswerRequest):
    state, context = get_project(project_id)
    if project_id in _ACTIVE:
        raise HTTPException(409, "Cannot change requirements while a run is active")
    question = next((q for q in context.clarification_questions if q.question_id == req.question_id), None)
    if not question:
        raise HTTPException(404, "Clarification question not found")
    if question.status != "PENDING":
        raise HTTPException(409, "Question already answered; restart understanding to revise requirements")
    if not req.answer.strip():
        raise HTTPException(422, "Answer must not be blank")
    invalidate(project_id)
    question.status, question.answer = "ANSWERED", req.answer
    unknown = next((u for u in context.unknowns if u.id == question.unknown_item_id), None)
    if unknown:
        resolved = unknown.model_copy(update={"description": req.answer, "source": RequirementSource.USER,
            "type": RequirementType.EXPLICIT, "confidence": 0.95,
            "evidence": f"Answer to {question.question}: {req.answer}"})
        context.unknowns = [u for u in context.unknowns if u.id != unknown.id]
        context.requirements = [r for r in context.requirements if r.id != unknown.id] + [resolved]
    context.version += 1
    state.revision = context.version
    context.decisions.append(DecisionRecord(decision_id=f"DEC-{uuid.uuid4().hex[:12].upper()}",
        category="USER_CLARIFICATION", selected_option=req.answer, rejected_alternatives=[],
        evidence=[f"User answered {question.question}: {req.answer}"], confidence=0.95))
    next_q = next((q for q in context.clarification_questions if q.status == "PENDING"), None)
    context.execution_state = "CLARIFICATION_REQUIRED" if next_q else "REQUIREMENTS_VALIDATED"
    await emit_event(project_id, "USER_CLARIFICATION_RECEIVED", "requirement_engine", "Requirement updated.",
                     {"version": context.version})
    return {"status": "clarified", "version": context.version, "execution_state": context.execution_state,
            "context": context.model_dump(mode="json"),
            "next_clarification": next_q.model_dump(mode="json") if next_q else None}


@router.get("/{project_id}/context")
async def get_project_context(project_id: str):
    return get_project(project_id)[1].model_dump(mode="json")


@router.post("/{project_id}/intake")
async def submit_intake_answer(project_id: str, req: ClarifyAnswerRequest):
    state, context = get_project(project_id)
    if project_id in _ACTIVE:
        raise HTTPException(409, "Project is running")
    invalidate(project_id)
    state.intake_qa[req.question_id] = req.answer
    context.version += 1
    state.revision = context.version
    context.execution_state = "INITIALIZED"
    save_project(project_id)
    return {"status": "success", "question_id": req.question_id}


async def _run_pipeline_background(project_id, model=None, resume=False):
    state, context = get_project(project_id)
    try:
        model = model or GeminiModelClient()
        async def emit(kind, role=None, message="", data=None):
            await emit_event(project_id, kind, role, message, data)
        context.execution_state = "ANALYZING"
        await asyncio.wait_for(run_specialists(state, context, model, emit, lambda: save_project(project_id), resume=resume),
                               get_settings().PIPELINE_TIMEOUT_SECONDS)
        spec = await BuildSpecCompiler().compile_model(context, state, model.generate)
        _BUILD_SPEC_STORE[project_id] = spec
        context.build_spec = spec.model_dump(mode="json")
        context.execution_state = "BUILD_SPEC_READY" if spec.status.value != "BLOCKED" else "BLOCKED"
        state.status = ProjectStatus.COMPLETED if context.execution_state == "BUILD_SPEC_READY" else ProjectStatus.BLOCKED
        await emit("BUILD_SPEC_COMPILED", "blueprint_architect", "Build specification compiled.", spec.model_dump(mode="json"))
        await emit("PIPELINE_COMPLETED", message="Planning complete; build and verification are separate stages.")
    except asyncio.CancelledError:
        context.execution_state = "CANCELLED"
        state.status = ProjectStatus.CANCELLED
        await emit_event(project_id, "PIPELINE_CANCELLED", message="Analysis cancelled.")
        raise
    except (ModelUnavailableError, ModelBudgetExceeded) as exc:
        context.execution_state = "BLOCKED"
        state.status = ProjectStatus.BLOCKED
        await emit_event(project_id, "PIPELINE_BLOCKED", message=str(exc))
    except Exception as exc:
        logger.exception("Analysis failed for %s", project_id)
        if context.execution_state != "REQUIRES_HUMAN":
            context.execution_state = "FAILED"
            state.status = ProjectStatus.FAILED
        kind = 'REQUIRES_HUMAN' if context.execution_state == 'REQUIRES_HUMAN' else 'PIPELINE_FAILED'
        await emit_event(project_id, kind, message=f"Planning stopped: {exc}")
    finally:
        if model:
            context.agent_outputs["model_usage"] = model.usage()
        save_project(project_id)
        _ACTIVE.discard(project_id)
        _RUN_TASKS.pop(project_id, None)


@router.post("/{project_id}/analyze")
async def start_analysis(project_id: str, resume: bool = False):
    state, context = get_project(project_id)
    if project_id in _ACTIVE:
        return {"status": "already_running", "project_id": project_id}
    if not context.requirements or any(q.status == "PENDING" for q in context.clarification_questions):
        raise HTTPException(409, "Complete requirement understanding and pending clarifications first")
    try:
        model = GeminiModelClient()
    except ModelUnavailableError as exc:
        context.execution_state = "BLOCKED"
        await emit_event(project_id, "PIPELINE_BLOCKED", message=str(exc))
        raise HTTPException(503, str(exc))
    if not resume:
        invalidate(project_id)
    else:
        _BUILD_SPEC_STORE.pop(project_id, None)
        context.build_spec = None
        context.architecture = None
        state.final_blueprint_markdown = None
    _ACTIVE.add(project_id)
    context.execution_state = "ANALYZING"
    save_project(project_id)
    _RUN_TASKS[project_id] = asyncio.create_task(_run_pipeline_background(project_id, model, resume=resume))
    return {"status": "started", "project_id": project_id}


@router.post("/{project_id}/cancel")
async def cancel_analysis(project_id: str):
    get_project(project_id)
    task = _RUN_TASKS.get(project_id)
    if not task:
        raise HTTPException(409, "No cancellable analysis is running")
    task.cancel()
    await asyncio.gather(task, return_exceptions=True)
    return {"status": "cancelled"}


@router.post("/{project_id}/compile-spec")
async def compile_build_spec(project_id: str):
    state, context = get_project(project_id)
    if project_id in _ACTIVE:
        raise HTTPException(409, "Project is running")
    if not all((state.product_spec, state.ai_spec, state.engineering_spec, state.ux_spec, state.security_report, state.qa_spec)):
        raise HTTPException(409, "Run the real specialist analysis before compiling a build specification")
    _ACTIVE.add(project_id)
    try:
        spec = await BuildSpecCompiler().compile_model(context, state, GeminiModelClient().generate)
        _BUILD_SPEC_STORE[project_id] = spec
        context.build_spec = spec.model_dump(mode="json")
        context.execution_state = "BUILD_SPEC_READY" if spec.status.value != "BLOCKED" else "BLOCKED"
        save_project(project_id)
        return spec.model_dump(mode="json")
    except ModelUnavailableError as exc:
        raise HTTPException(503, str(exc))
    finally:
        _ACTIVE.discard(project_id)


@router.get("/{project_id}/build-spec")
async def get_build_spec(project_id: str):
    get_project(project_id)
    spec = _BUILD_SPEC_STORE.get(project_id)
    if not spec:
        raise HTTPException(404, "No build specification; run analysis first")
    return spec.model_dump(mode="json")


@router.post("/{project_id}/approve-build")
async def approve_build(project_id: str, req: ApprovalRequest):
    state, context = get_project(project_id)
    spec = _BUILD_SPEC_STORE.get(project_id)
    if project_id in _ACTIVE:
        raise HTTPException(409, "Cannot approve a specification while execution is active")
    if not spec or spec.version != req.version or context.version != req.version or spec.status.value == "BLOCKED":
        raise HTTPException(409, "Approval requires the current, non-blocked build specification")
    context.execution_state = "BUILD_SPEC_APPROVED"
    await emit_event(project_id, "BUILD_SPEC_APPROVED", message="Current build specification approved.")
    return {"status": "approved", "version": req.version}


@router.post("/{project_id}/conflicts/{conflict_id}/resolve")
async def resolve_conflict(project_id: str, conflict_id: str, req: ConflictResolutionRequest):
    state, context = get_project(project_id)
    if project_id in _ACTIVE:
        raise HTTPException(409, "Wait for analysis to stop before resolving conflicts")
    conflict = next((c for c in context.conflicts if c.conflict_id == conflict_id), None)
    if not conflict:
        raise HTTPException(404, "Conflict not found")
    decision_id = f"DEC-{uuid.uuid4().hex[:12].upper()}"
    decision = DecisionRecord(decision_id=decision_id, category="CONFLICT_RESOLUTION",
        selected_option=req.decision, rejected_alternatives=[], evidence=[conflict.issue], confidence=0.0)
    # Re-run specialists against the human choice rather than merely adding an
    # ADR while leaving contradictory implementation specifications intact.
    invalidate(project_id)
    context.decisions.append(decision)
    context.constraints.append(ExtractedRequirementItem(id=decision_id, dimension="constraints",
        title="User conflict resolution", description=req.decision, type=RequirementType.EXPLICIT,
        source=RequirementSource.USER, confidence=0.95, evidence=f"User resolution of {conflict_id}"))
    context.version += 1
    state.revision = context.version
    context.execution_state = "REQUIREMENTS_VALIDATED"
    await emit_event(project_id, "CONFLICT_RESOLVED", "conflict_resolver", "Decision recorded; specialist reanalysis required.")
    return {"status": "reanalysis_required", "context": context.model_dump(mode="json")}


@router.post("/{project_id}/build")
async def start_autonomous_build(project_id: str, resume: bool = False):
    state, context = get_project(project_id)
    if project_id in _ACTIVE:
        raise HTTPException(409, "A project operation is already running")
    spec = _BUILD_SPEC_STORE.get(project_id)
    if not spec or spec.status.value == "BLOCKED" or spec.version != context.version:
        raise HTTPException(409, "A current, non-blocked build specification is required")
    if context.mode == "GUIDED" and context.execution_state != "BUILD_SPEC_APPROVED":
        raise HTTPException(409, "Approve this build specification before guided execution")
    try:
        model = GeminiModelClient()
    except ModelUnavailableError as exc:
        raise HTTPException(503, str(exc))
    _ACTIVE.add(project_id)
    context.execution_state = "BUILDING"
    save_project(project_id)
    loop = asyncio.get_running_loop()
    worker = None
    def callback(kind, data):
        # asyncio queues and conditions are only touched on the event-loop thread.
        future = asyncio.run_coroutine_threadsafe(emit_event(project_id, kind, "coding_agent", f"Build: {kind}", data), loop)
        future.result(timeout=15)
    try:
        workspace = WORKSPACES / project_id / f"v{context.version}"
        if not workspace.resolve().is_relative_to(WORKSPACES.resolve()):
            raise HTTPException(400, "Workspace path escapes the generated-project root")
        orchestrator = CodingOrchestrator(workspace, on_event_callback=callback, model_client=model)
        worker = asyncio.create_task(asyncio.to_thread(orchestrator.execute_build, spec, resume=resume))
        report = await asyncio.shield(worker)
        context.execution_state = report.status
        context.agent_outputs["build_report"] = report.model_dump(mode="json")
        context.agent_outputs["build_model_usage"] = model.usage()
        save_project(project_id)
        return report.model_dump(mode="json")
    except asyncio.CancelledError:
        # HTTP disconnect cannot cancel a Python worker. Keep the operation lock
        # until it finishes and persist its real outcome.
        if worker:
            try:
                report = await worker
                context.execution_state = report.status
                context.agent_outputs["build_report"] = report.model_dump(mode="json")
            except Exception:
                context.execution_state = "FAILED"
        raise
    except Exception:
        context.execution_state = "FAILED"
        logger.exception("Build failed for %s", project_id)
        await emit_event(project_id, "BUILD_FAILED", message="Build failed; see backend logs.")
        raise HTTPException(500, "Build failed")
    finally:
        save_project(project_id)
        _ACTIVE.discard(project_id)


@router.post("/{project_id}/open-editor")
async def open_in_editor(project_id: str):
    state, context = get_project(project_id)
    if context.execution_state != "VERIFIED" or project_id in _ACTIVE:
        raise HTTPException(409, "Only a verified, inactive project can be opened automatically")
    workspace = WORKSPACES / project_id / f"v{context.version}"
    success, message = VSCodeLauncher.open_project(workspace, require_verified_tests=True)
    return {"success": success, "message": message, "workspace": str(workspace)}


@router.get("/{project_id}/stream")
async def stream_events(project_id: str, request: Request):
    get_project(project_id)
    try:
        sequence = max(0, int(request.headers.get("last-event-id", request.query_params.get("after", "0"))))
    except ValueError:
        raise HTTPException(400, "Invalid event sequence")
    async def event_generator():
        nonlocal sequence
        signal = _SIGNALS.setdefault(project_id, asyncio.Condition())
        while not await request.is_disconnected():
            async with signal:
                events = _PERSISTENCE.events_after(project_id, sequence)
                if not events:
                    try:
                        await asyncio.wait_for(signal.wait(), timeout=15)
                    except asyncio.TimeoutError:
                        pass
            if events:
                for sequence, payload in events:
                    yield f"id: {sequence}\ndata: {json.dumps(payload)}\n\n"
            else:
                yield ": heartbeat\n\n"
    return StreamingResponse(event_generator(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})
