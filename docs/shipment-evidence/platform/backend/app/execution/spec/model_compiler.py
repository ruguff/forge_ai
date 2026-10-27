"""Requirement-grounded model compilation with platform-owned validation."""
from pathlib import PurePosixPath
from app.harness.base_harness import AgentExecutionHarness
from app.execution.spec.build_spec_models import BuildSpec, BuildSpecStatus, ProjectType
from app.execution.tasks.task_graph import TaskGraph


def contains_response_schema(value):
    """Acceptance subsets are example response data, never JSON Schemas."""
    if isinstance(value, list):
        return any(contains_response_schema(item) for item in value)
    if isinstance(value, dict):
        if ('$schema' in value or '$ref' in value
                or value.get('type') == 'object' and isinstance(value.get('properties'), dict)
                or value.get('type') == 'array' and 'items' in value):
            return True
        return any(contains_response_schema(item) for item in value.values())
    return False


def validate_spec(spec, context):
    errors = []
    relational = spec.source_generation_strategy == 'RELATIONAL_CRUD'
    catalogue = spec.source_generation_strategy == 'CATALOGUE'
    provider = spec.source_generation_strategy == 'RAZORPAY_TEST'
    if spec.razorpay_test_contract is not None and not provider:
        errors.append('Razorpay test contract requires reviewed RAZORPAY_TEST strategy.')
    simulation = spec.source_generation_strategy == 'PAYMENT_SIMULATOR'
    ordering = spec.source_generation_strategy in ('ORDERS','PAYMENT_SIMULATOR','RAZORPAY_TEST')
    if spec.payment_simulation_contract is not None and not simulation:
        errors.append('Payment simulation contract requires reviewed PAYMENT_SIMULATOR strategy.')
    identity = spec.source_generation_strategy in ('IDENTITY','ORDERS','PAYMENT_SIMULATOR','RAZORPAY_TEST')
    if spec.order_contract is not None and not ordering:
        errors.append('Order contract requires reviewed ORDERS strategy.')
    if ordering:
        if provider:
            from app.execution.agent.razorpay import validate_scope
        elif simulation:
            from app.execution.agent.payments import validate_scope
        else:
            from app.execution.agent.orders import validate_scope
        try:validate_scope(spec)
        except ValueError as exc:errors.append(str(exc))
    if spec.identity_contract is not None and not identity:
        errors.append('Identity contract requires reviewed IDENTITY generation strategy.')
    if identity and not ordering:
        from app.execution.agent.identity import validate_scope
        try:
            validate_scope(spec)
        except ValueError as exc:
            errors.append(str(exc))
    if spec.catalogue_contract is not None and not (catalogue or identity):
        errors.append('Catalogue contract requires the reviewed CATALOGUE generation strategy.')
    if catalogue:
        from app.execution.agent.catalogue import validate_scope
        try:
            validate_scope(spec)
        except ValueError as exc:
            errors.append(str(exc))
    if relational:
        from app.execution.agent.relational import schema_for
        try:
            schema_for(spec)
        except ValueError as exc:
            errors.append(str(exc))
    if spec.commerce_contract is not None:
        errors.append('Commerce contract execution is not yet available in the current runtime; no CRUD substitution is permitted.')
    if "fastapi" not in spec.tech_stack.backend_framework.lower():
        errors.append("The current isolated runtime supports FastAPI backends only.")
    if spec.project_type == ProjectType.FULLSTACK_WEB and "react" not in spec.tech_stack.frontend_framework.lower():
        errors.append("The current isolated runtime supports React frontends only.")
    if spec.tech_stack.primary_database.lower() not in (("sqlite", "postgresql") if relational or catalogue or identity else ("sqlite", "none", "in-memory", "in memory")):
        errors.append("The current isolated runtime supports SQLite or in-memory storage only.")
    # User-declared technology preferences remain binding. Unsupported choices
    # cause a validation failure rather than being silently replaced.
    for item in context.requirements + context.constraints:
        if item.source.value != "USER" or item.dimension not in ("technology_preferences", "tech_stack", "constraints"):
            continue
        value = item.description.lower()
        for unsupported in ("django", "flask", "express", "mongodb", "postgresql", "mysql", "angular", "vue", "redis"):
            if unsupported == 'postgresql' and (relational or catalogue or identity):
                continue
            if unsupported in value and not any(phrase in value for phrase in (f"not {unsupported}", f"no {unsupported}", f"without {unsupported}")):
                errors.append(f"Explicit user technology {unsupported} is outside the supported runtime; clarification is required.")
    if spec.project_type not in (ProjectType.FULLSTACK_WEB, ProjectType.BACKEND_API):
        errors.append("Only FULLSTACK_WEB and BACKEND_API are supported in this MVP.")
    required = {"README.md", "backend/app/__init__.py", "backend/app/main.py", "backend/requirements.txt"}
    if spec.project_type == ProjectType.FULLSTACK_WEB:
        required |= {"frontend/package.json", "frontend/index.html", "frontend/tsconfig.json",
                     "frontend/vite.config.ts", "frontend/src/main.tsx", "frontend/src/App.tsx"}
    paths = [f.file_path for f in spec.files_to_create]
    max_files = 48 if simulation or provider else 40
    if not paths or len(paths) > max_files or len(paths) != len(set(paths)):
        errors.append(f"File graph must have 1–{max_files} unique paths.")
    for file in spec.files_to_create:
        path = PurePosixPath(file.file_path)
        if (path.is_absolute() or ".." in path.parts or "\\" in file.file_path or ":" in file.file_path
            or not path.parts or any(p.startswith(".") for p in path.parts)
            or (file.file_path != "README.md" and path.parts[0] not in ("backend", "frontend"))):
            errors.append(f"Unsafe or unsupported source path: {file.file_path}")
    if not required.issubset(paths):
        errors.append(f"Missing startup files: {sorted(required - set(paths))}")
    requirement_ids = {r.id for r in context.requirements}
    if not requirement_ids.issubset({r.id for r in spec.requirements}):
        errors.append("Every input requirement must retain its original ID.")
    source_by_id = {r.id: r.source for r in context.requirements}
    for req in spec.requirements:
        if req.id in source_by_id:
            expected = "INFERRED" if source_by_id[req.id].value == "INFERENCE" else source_by_id[req.id].value
            if req.source.value != expected:
                errors.append(f"Changed provenance for {req.id}.")
    if not spec.acceptance_checks:
        errors.append("Define platform-controlled HTTP acceptance checks before coding.")
    if spec.project_type == ProjectType.FULLSTACK_WEB and not spec.browser_checks:
        errors.append("Full-stack websites require platform-controlled browser journey checks.")
    for journey in spec.browser_checks:
        if not journey.get("steps"):
            errors.append("Browser journeys need at least one step.")
        if not journey.get("requirements") or not set(journey.get("requirements", [])).issubset(requirement_ids):
            errors.append("Browser journeys need original requirement IDs.")
        if not any(s.get("action") in ("visible", "text", "hidden") for s in journey.get("steps", [])):
            errors.append("Browser journeys must assert an observable result.")
        steps = journey.get('steps', [])
        last_mutation = max((i for i, step in enumerate(steps) if step.get('action') in ('fill', 'click', 'select', 'press')), default=-1)
        if last_mutation >= 0 and not any(step.get('action') in ('visible', 'text', 'hidden') for step in steps[last_mutation + 1:]):
            errors.append('Browser journeys must assert the result after the final interaction.')
        for step in journey.get("steps", []):
            if step.get("action") not in ("goto", "fill", "click", "visible", "text", "hidden", "select", "press"):
                errors.append("Unsupported browser action.")
            if step.get("action") == "goto" and (not step.get("path", "").startswith("/") or step["path"].startswith("//")):
                errors.append("Browser navigation must be local.")
            if step.get('action') == 'goto' and step.get('path', '').startswith('/api'):
                errors.append('Browser journeys must navigate to UI pages, never API JSON routes.')
            if step.get("action") != "goto" and not isinstance(step.get("selector"), str):
                errors.append("Browser interaction requires a selector.")
            if step.get("action") in ("fill", "text", "select", "press") and not isinstance(step.get("value"), str):
                errors.append("Browser fill/text requires a string value.")
            import re
            if re.search(r'\[\d+\]', step.get('selector') or ''):
                errors.append('Use valid CSS selectors such as :first-child, not array indexing [0].')
            if ':contains(' in (step.get('selector') or ''):
                errors.append('Use a text assertion or :has-text(), not the unsupported :contains() selector.')
    for check in spec.acceptance_checks:
        if contains_response_schema(check.get('body_contains')):
            errors.append('body_contains must be actual expected response data, not a JSON Schema. '
                          'For example POST {"title":"Test Note","body":"Hello"} should assert '
                          '{"title":"Test Note","body":"Hello"}, without type/properties schema declarations.')
        if 'body_contains' in check and (check.get('status') == 204 or check.get('body_contains') in ({}, [], None)):
            errors.append('Acceptance response assertions must be meaningful and cannot parse an empty 204 response.')
        if check.get('method') in ('POST', 'PUT', 'PATCH') and 200 <= check.get('status', 0) < 300 and not isinstance(check.get('json'), dict):
            errors.append('Successful mutation acceptance checks must supply their request JSON.')
        if (check.get("method") not in ("GET", "POST", "PUT", "PATCH", "DELETE")
            or not isinstance(check.get("path"), str) or not check["path"].startswith("/api/")
            or not isinstance(check.get("status"), int)
            or not isinstance(check.get("requirements"), list)
            or not check.get("requirements")
            or not set(check["requirements"]).issubset(requirement_ids)):
            errors.append("Acceptance cases need API path, method, status and valid requirement IDs.")
    covered = {r for c in spec.acceptance_checks for r in c.get("requirements", [])}
    covered |= {r for j in spec.browser_checks for r in j.get("requirements", [])}
    functional = {r.id for r in context.requirements if r.dimension in ("functional", "functional_requirements")}
    if not functional.issubset(covered):
        errors.append(f"Acceptance checks omit functional requirements: {sorted(functional - covered)}")
    try:
        spec.generation_mode = "MODEL"
        TaskGraph().build_from_spec(spec)
    except Exception as exc:
        errors.append(str(exc))
    return errors


async def compile_model(context, state, llm_client):
    if any(q.status == "PENDING" for q in context.clarification_questions) or context.conflicts:
        raise ValueError("Resolve material clarifications and contradictions before compilation.")
    if not all((state.product_spec, state.ai_spec, state.engineering_spec, state.ux_spec, state.security_report, state.qa_spec)):
        raise ValueError("All specialist artifacts are required.")
    prompt = """Compile a runnable React 18/TypeScript 5/Vite 5 + FastAPI website specification.
Use the supplied requirements, constraints, decisions and specialist outputs as authoritative.
Preserve original requirement IDs and provenance. Do not treat inferred features as user requirements.
Support FULLSTACK_WEB or BACKEND_API only. Implement requested business workflows.
Backend must export app from backend/app/main.py, with /api routes. Single-entity persistence uses SQLite.
Bounded related CRUD may use PostgreSQL with the typed relational_contract and RELATIONAL_CRUD strategy.
Public read-only catalogues may use catalogue_contract and CATALOGUE strategy with PostgreSQL and the reviewed module manifest.
Catalogue accounts, owned addresses and authorized administration use catalogue_contract plus identity_contract and IDENTITY strategy, auth_provider=session. Server-priced carts, unpaid orders, snapshots, idempotency and inventory reservation use order_contract plus identity_contract and ORDERS strategy. Explicit offline simulation uses payment_simulation_contract (version=1, mode=offline_simulator, refunds=admin_full_only) with PAYMENT_SIMULATOR strategy and the preceding order/identity/catalogue contracts. Razorpay TEST integration uses razorpay_test_contract (version=1,mode=razorpay_test,currency=INR,refunds=admin_full_only), RAZORPAY_TEST strategy and preceding order/identity/catalogue contracts; it excludes the simulator. Never emit credentials. Actual provider verification needs an external test account. Live collection, fulfillment and partial refunds remain unsupported.
Declare every source/configuration file and file dependencies. Include backend/requirements.txt,
README.md and all frontend startup files: index.html, package.json, tsconfig.json, vite.config.ts,
src/main.tsx and src/App.tsx. No secrets, shell scripts or package lifecycle hooks.
Define acceptance_checks as ordered HTTP cases with method, path, json (optional), status,
body_contains (optional nonempty JSON object/list subset), and requirements (original IDs).
Cover every functional requirement with meaningful cases. The platform freezes checks before coding.
For full-stack websites include browser_checks: [{name, requirements: [original IDs], steps: [...]}].
Steps support goto with path, fill with selector/value, click with selector,
visible or hidden with selector, and text with selector/value. Assert the result AFTER the final interaction.
Use valid CSS selectors, never array indexing [0]. Successful POST/PUT/PATCH cases need request JSON.
Include a meaningful primary user journey.
If browser-only or unsupported functionality cannot be expressed, do not silently omit it.
Do not claim security, load, browser or accessibility checks passed. Confidence is uncalibrated.
Return only JSON conforming to BuildSpec."""
    from app.agents.model_client import LocalModelClient
    if isinstance(getattr(llm_client, '__self__', None), LocalModelClient):
        from app.execution.spec.local_compiler import compile_local
        return await compile_local(context, state, llm_client, prompt, validate_spec)
    result = await AgentExecutionHarness(target_schema=BuildSpec, agent_name="BuildSpecCompiler",
        system_prompt=prompt, llm_client=llm_client,
        extra_lint_rules=[lambda spec: validate_spec(spec, context)]).execute({
            "context": context.model_dump(mode="json"), "specialists": state.model_dump(mode="json")})
    if not result.success:
        raise RuntimeError("Build spec validation failed: " + str(result.validation_errors + result.lint_violations))
    spec = result.output
    spec.project_id, spec.project_name, spec.version = context.project_id, context.project_name, context.version
    spec.generation_mode, spec.status, spec.blocked_reasons = "MODEL", BuildSpecStatus.COMPILED, None
    spec.overall_confidence = 0.0
    if spec.source_generation_strategy == 'RAZORPAY_TEST':
        from app.execution.agent.razorpay import prepare_spec
        spec = prepare_spec(spec)
    elif spec.source_generation_strategy == 'PAYMENT_SIMULATOR':
        from app.execution.agent.payments import prepare_spec
        spec = prepare_spec(spec)
    elif spec.source_generation_strategy == 'ORDERS':
        from app.execution.agent.orders import prepare_spec
        spec = prepare_spec(spec)
    elif spec.source_generation_strategy == 'IDENTITY':
        from app.execution.agent.identity import prepare_spec
        spec = prepare_spec(spec)
    elif spec.source_generation_strategy == 'CATALOGUE':
        from app.execution.agent.catalogue import prepare_spec
        spec = prepare_spec(spec)
    return spec
