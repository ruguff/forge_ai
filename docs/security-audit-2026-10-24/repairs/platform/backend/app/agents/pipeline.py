"""Real specialist execution with dependency ordering and immutable inputs."""
import asyncio
import time
import hashlib
import json
from app.agents.product_agent import ProductAgent
from app.agents.aiml_agent import AIMLAgent
from app.agents.engineering_agent import EngineeringAgent
from app.agents.ux_agent import UXAgent
from app.agents.security_agent import SecurityAgent
from app.agents.qa_agent import QAAgent
from app.agents.conflict_resolver import ConflictResolver
from app.agents.final_architect import FinalArchitect
from app.models.schemas import ProjectStatus
from app.config import get_settings
from app.agents.model_client import ModelBudgetExceeded, ModelUnavailableError


async def run_specialists(state, context, model, emit, save, resume=False):
    fields = ('product_spec', 'ai_spec', 'engineering_spec', 'ux_spec', 'security_report', 'qa_spec')
    # A conservative chain: any recomputed stage invalidates all later reuse.
    identity = {'revision': 1, 'version': context.version, 'request': context.raw_request,
        'requirements': [r.model_dump(mode='json') for r in context.requirements],
        'constraints': [r.model_dump(mode='json') for r in context.constraints],
        'decisions': [r.model_dump(mode='json') for r in context.decisions], 'mode': context.mode}
    fingerprint = hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()
    saved = context.agent_outputs.get('_analysis_checkpoint', {})
    reuse = (resume and isinstance(saved, dict) and saved.get('fingerprint') == fingerprint
             and isinstance(saved.get('outputs'), dict))
    checkpoint = saved if reuse else {'fingerprint': fingerprint, 'outputs': {}}
    context.agent_outputs['_analysis_checkpoint'] = checkpoint
    if not reuse:
        for field in fields:
            setattr(state, field, None)
            context.agent_outputs.pop(field, None)

    async def execute(role, agent_class, field):
        nonlocal reuse
        output = getattr(state, field)
        if reuse and output is not None and checkpoint['outputs'].get(field) == output.model_dump(mode='json'):
            await emit('AGENT_RECOVERED', role, f'Recovered validated {role} checkpoint.')
            return
        reuse = False
        for remaining in fields[fields.index(field):]:
            checkpoint['outputs'].pop(remaining, None)
            setattr(state, remaining, None)
            context.agent_outputs.pop(remaining, None)
        save()
        started = time.monotonic()
        await emit("AGENT_STARTED", role, f"Running {role}.")
        inputs = state.model_dump(mode="json")
        inputs["project_context"] = {
            "raw_request": context.raw_request, "version": context.version,
            "requirements": [r.model_dump(mode="json") for r in context.requirements],
            "constraints": [r.model_dump(mode="json") for r in context.constraints],
            "decisions": [d.model_dump(mode="json") for d in context.decisions],
            "mode": context.mode,
            "execution_capabilities": {
                "supported_stack": "React 18 + TypeScript 5 + Vite 5 + FastAPI; single-entity SQLite CRUD, bounded related CRUD with SQLite/PostgreSQL, PostgreSQL catalogues with variants/images/search/filters, reviewed server-session customer accounts and authorized catalogue administration, plus the reviewed ORDERS module for server-priced carts, unpaid orders, address/price snapshots, idempotency, stock reservation, cancellation and expiry. Payment collection, fulfillment and refunds remain unsupported.",
                "external_services": "Unavailable in the offline verification container",
                "instruction": "Respect user choices. Report incompatible explicit choices as limitations; do not silently substitute technologies.",
            },
        }
        try:
            result = await agent_class(llm_client=model.generate).analyze(inputs)
        except (ModelBudgetExceeded, ModelUnavailableError) as exc:
            await emit("AGENT_FAILED", role, str(exc), {"errors": [str(exc)], "lint": []})
            raise
        if not result.success:
            details = result.validation_errors + result.lint_violations
            message = f"{role} failed after {result.attempts} attempts: " + "; ".join(details)
            await emit("AGENT_FAILED", role, message,
                       {"errors": result.validation_errors, "lint": result.lint_violations})
            raise ModelUnavailableError(message)
        setattr(state, field, result.output)
        context.agent_outputs[field] = result.output.model_dump(mode="json")
        checkpoint['outputs'][field] = result.output.model_dump(mode='json')
        save()
        await emit("AGENT_COMPLETED", role, f"Validated {role} output.",
                   {"attempts": result.attempts, "elapsed_seconds": round(time.monotonic() - started, 2)})

    state.status = ProjectStatus.ANALYZING_CORE
    await execute("product_manager", ProductAgent, "product_spec")
    await execute("aiml_architect", AIMLAgent, "ai_spec")
    state.status = ProjectStatus.ANALYZING_ENGINEERING
    await execute("engineering_lead", EngineeringAgent, "engineering_spec")
    if get_settings().LLM_PROVIDER == "lmstudio" or resume:
        await execute("ux_designer", UXAgent, "ux_spec")
        await execute("security_auditor", SecurityAgent, "security_report")
    else:
        pending = [asyncio.create_task(execute("ux_designer", UXAgent, "ux_spec")),
                   asyncio.create_task(execute("security_auditor", SecurityAgent, "security_report"))]
        try:
            await asyncio.gather(*pending)
        finally:
            for task in pending:
                if not task.done():
                    task.cancel()
            await asyncio.gather(*pending, return_exceptions=True)
    state.status = ProjectStatus.ANALYZING_VERIFICATION
    await execute("qa_strategist", QAAgent, "qa_spec")
    state.status = ProjectStatus.RESOLVING_CONFLICTS
    conflicts = ConflictResolver().detect_conflicts(state.model_dump(mode="json"))
    state.detected_conflicts = conflicts
    context.conflicts = conflicts
    for conflict in conflicts:
        await emit("CONFLICT_DETECTED", "conflict_resolver", conflict.issue, conflict.model_dump(mode="json"))
    if conflicts:
        # Utility scores alone must not silently override constraints or leave
        # contradictory agent specifications unchanged.
        state.status = ProjectStatus.AWAITING_HUMAN_REVIEW
        context.execution_state = "REQUIRES_HUMAN"
        save()
        raise RuntimeError("Specialist contradictions require review before build compilation.")
    state.status = ProjectStatus.ARCHITECTING
    await emit("ARCHITECT_STARTED", "blueprint_architect", "Compiling validated specialist outputs.")
    state.final_blueprint_markdown = FinalArchitect().generate_blueprint(state)
    context.architecture = state.final_blueprint_markdown
    save()
    await emit("BLUEPRINT_GENERATED", "blueprint_architect", "Planning blueprint compiled; code is not yet verified.",
               {"blueprint": state.final_blueprint_markdown})
