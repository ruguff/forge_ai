"""Compile bounded local-model sections without asking the model to recopy provenance."""
import copy
from functools import partial
from typing import Literal, Any, Annotated
from pydantic import create_model, BaseModel, Field
from app.harness.base_harness import AgentExecutionHarness
from app.execution.spec.build_spec_models import BuildSpec, BuildRequirementItem, TargetFileDef


class LocalFile(TargetFileDef):
    file_path: str = Field(pattern=r'^(README\.md|backend/[A-Za-z0-9_./-]+|frontend/[A-Za-z0-9_./-]+)$')
    dependencies: list[Annotated[str, Field(pattern=r'^(README\.md|backend/[A-Za-z0-9_./-]+|frontend/[A-Za-z0-9_./-]+)$')]] = Field(default_factory=list)


RUNTIME_FILES = {
    'backend/app/__init__.py': ('Backend package marker', []),
    'backend/requirements.txt': ('Supported backend dependencies', []),
    'backend/app/main.py': ('FastAPI app, declared API contracts and local persistence', ['backend/app/__init__.py', 'backend/requirements.txt']),
    'backend/tests/test_app.py': ('Pytest cases for input validation and declared API workflows using a temporary SQLite database', ['backend/app/main.py']),
    'frontend/package.json': ('React/Vite scripts and supported dependencies', []),
    'frontend/tsconfig.json': ('TypeScript compiler configuration', []),
    'frontend/vite.config.ts': ('Vite React configuration and local API proxy', ['frontend/package.json']),
    'frontend/src/App.tsx': ('Implement declared user journeys and UI selectors', ['backend/app/main.py', 'frontend/package.json']),
    'frontend/src/main.tsx': ('Mount the App component', ['frontend/src/App.tsx']),
    'frontend/index.html': ('HTML entry pointing to src/main.tsx', ['frontend/src/main.tsx']),
    'README.md': ('Document actual setup, behavior and limitations', ['backend/app/main.py', 'frontend/package.json']),
}


def runtime_manifest(files, project_type, requirement_ids):
    paths = [item.file_path for item in files]
    if len(paths) != len(set(paths)):
        raise ValueError('Duplicate file paths in model file section')
    additional_paths = set(paths) - set(RUNTIME_FILES)
    result = [item for item in files if item.file_path not in RUNTIME_FILES]
    for path, (description, dependencies) in RUNTIME_FILES.items():
        if project_type == 'BACKEND_API' and path.startswith('frontend/'):
            continue
        deps = [d for d in dependencies if project_type != 'BACKEND_API' or not d.startswith('frontend/')]
        existing = next((item for item in files if item.file_path == path), None)
        if existing:
            deps += [d for d in existing.dependencies if d in additional_paths and d not in deps]
        result.append(TargetFileDef(file_path=path, description=description,
            target_module=path.split('/')[0], dependencies=deps, traceable_requirements=requirement_ids))
    return result


class HttpCheck(BaseModel):
    method: Literal['GET', 'POST', 'PUT', 'PATCH', 'DELETE']
    path: str = Field(pattern=r'^/api/')
    status: int
    request_json: dict[str, Any] | None = Field(default=None, alias='json')
    body_contains: Annotated[dict[str, Any], Field(min_length=1)] | Annotated[list[Any], Field(min_length=1)] | None = None
    requirements: list[str] = Field(min_length=1)


class BrowserStep(BaseModel):
    action: Literal['goto', 'fill', 'click', 'visible', 'text', 'hidden', 'select', 'press']
    path: str | None = None
    selector: str | None = None
    value: str | None = None


class BrowserJourney(BaseModel):
    name: str
    requirements: list[str] = Field(min_length=1)
    steps: list[BrowserStep] = Field(min_length=1)


def copy_requirement(item):
    return BuildRequirementItem(id=item.id, title=item.title, description=item.description,
        dimension=item.dimension, source='INFERRED' if item.source.value == 'INFERENCE' else item.source.value,
        confidence=item.confidence, traceability_path=[item.id])


def implementation_decisions(engineering):
    # Keep chosen architecture and its operational limitations. Rejected options
    # and confidence commentary remain in the original specialist audit report.
    data = engineering.model_dump(mode='json')
    return {key: {k: value[k] for k in ('selected', 'version', 'why', 'tradeoffs', 'failure_conditions') if k in value}
            if isinstance(value, dict) and 'selected' in value else value for key, value in data.items()}


async def compile_local(context, state, llm_client, prompt, validate):
    groups = [
        ('architecture', ['project_type', 'tech_stack', 'database_entities', 'api_endpoints', 'relational_contract', 'catalogue_contract', 'identity_contract', 'order_contract', 'payment_simulation_contract', 'razorpay_test_contract']),
        ('files', ['ui_components', 'dependencies', 'files_to_create', 'environment_variables']),
        ('checks', ['acceptance_checks', 'browser_checks', 'test_requirements']),
        ('policy', ['security_requirements', 'deployment_requirements', 'decisions']),
    ]
    generated = {}
    requirements = [copy_requirement(item) for item in context.requirements]
    base = {'raw_request': context.raw_request,
            'requirements': [r.model_dump(mode='json') for r in requirements],
            'constraints': [c.model_dump(mode='json') for c in context.constraints],
            'decisions': [d.model_dump(mode='json') for d in context.decisions]}
    for name, fields in groups:
        section_schema = create_model('BuildSpec_' + name, **{
            field: (BuildSpec.model_fields[field].annotation, copy.deepcopy(BuildSpec.model_fields[field]))
            for field in fields})
        if name == 'files':
            section_schema = create_model('BuildSpecFiles', __base__=section_schema,
                files_to_create=(list[LocalFile], Field(default_factory=list, max_length=30)))
        if name == 'checks':
            section_schema = create_model('BuildSpecChecks', __base__=section_schema,
                acceptance_checks=(list[HttpCheck], Field(min_length=1)),
                browser_checks=(list[BrowserJourney], Field(min_length=1)))
        section_context = dict(base)
        if name == 'architecture':
            section_context['engineering'] = implementation_decisions(state.engineering_spec)
            section_context['ai'] = state.ai_spec.model_dump(mode='json')
        elif name == 'files':
            section_context['architecture'] = generated
            section_context['ux'] = state.ux_spec.model_dump(mode='json')
            section_context['platform_startup_files'] = list(RUNTIME_FILES)
        elif name == 'checks':
            section_context['api_endpoints'] = generated['api_endpoints']
            section_context['ui_components'] = generated['ui_components']
            section_context['qa_cases'] = [c.model_dump(mode='json') for c in state.qa_spec.critical_test_cases]
            if generated.get('source_generation_strategy') == 'RELATIONAL_CRUD':
                section_context['ui_contract'] = {
                    'version':1, 'namespace':'table name in lowercase with underscores replaced by hyphens',
                    'selectors':'[data-testid="NAMESPACE-field-FIELD"], NAMESPACE-create, NAMESPACE-save, NAMESPACE-row, NAMESPACE-edit, NAMESPACE-delete; rows/actions also have data-record-id',
                    'navigation':'nav button with entity_name as visible text'}
            if generated.get('source_generation_strategy') in ('CATALOGUE','IDENTITY','ORDERS','PAYMENT_SIMULATOR','RAZORPAY_TEST'):
                from app.execution.spec.catalogue_ui import ui_manifest
                section_context['ui_contract'] = ui_manifest()
                section_context['catalogue_data'] = generated['catalogue_contract']
                if generated.get('source_generation_strategy') in ('IDENTITY','ORDERS','PAYMENT_SIMULATOR','RAZORPAY_TEST'):
                    from app.execution.spec.identity_ui import ui_manifest as identity_manifest
                    section_context['identity_ui_contract']=identity_manifest()
                if generated.get('source_generation_strategy') == 'PAYMENT_SIMULATOR':
                    section_context['payment_ui_contract']={'version':1,'page':'/orders','admin_page':'/admin/orders','panel':'payment-simulator-ORDER_ID','notice':'payment-notice','status':'payment-status','scope':'offline simulation only; never provider verification'}
                if generated.get('source_generation_strategy') == 'RAZORPAY_TEST':
                    section_context['payment_ui_contract']={'version':1,'page':'/orders','admin_page':'/admin/orders','panel':'razorpay-test-ORDER_ID','notice':'payment-notice','status':'payment-status','scope':'test provider only; credentials absent in generated tests; expect unavailable, never invent provider success'}
        else:
            section_context['tech_stack'] = generated['tech_stack']
            section_context['security'] = state.security_report.model_dump(mode='json')
        instructions = (prompt + f'\nGenerate only the {name} section fields in the schema. '
            'Do not repeat requirements or project identity. Keep descriptions concise. '
            'For 2–12 related entities, use relational_contract version 1 with relationships '
            '(source_table, source_column, target_table, target_column, on_delete). '
            'Leave each entity relationships text list empty. Each entity needs one integer primary key, '
            'integer/string/text fields without defaults, and canonical GET/POST /api/TABLE, PUT/DELETE /api/TABLE/{record_id}. '
            'This relational CRUD mode supports SQLite or PostgreSQL but no authentication or commerce business rules. '
            'Single-entity projects should omit relational_contract. '
            'For a PUBLIC READ-ONLY product catalogue, use catalogue_contract version 1, '
            'PostgreSQL, auth_provider=None, plain CSS, no database_entities and no relational_contract. '
            'Provide store_name, tagline, currency (INR/USD/EUR/GBP), categories and products. '
            'Keep initial catalogue seed small: 2 products with 1 or 2 variants each. '
            'Product fields: slug, category_slug, name, description, material, active, variants, images. '
            'Variant fields: sku, label, options object, price_minor integer, stock_quantity integer, active. '
            'Images use only asset pack/bottle/lamp/stool/tote/blanket and a meaningful alt. '
            'Declare only GET /api/store, /api/categories, /api/products, /api/products/{slug}. '
            'Catalogue browsing supports search, category/price/in-stock filtering and pagination. '
            'For customer accounts, owned addresses and authorized catalogue administration, add identity_contract version 1, '
            'public_origin (exact HTTPS origin), allow_local_http=false, session_idle_seconds=1800, '
            'session_absolute_seconds=28800, recovery_seconds=900 and auth_provider=session. '
            'Explicit local demos may use http://127.0.0.1:3001 and allow_local_http=true. '
            'Only when OFFLINE payment simulation is explicitly requested, add payment_simulation_contract {version:1,mode:offline_simulator,refunds:admin_full_only} alongside identity_contract and order_contract. This requires PostgreSQL and uses reviewed PAYMENT_SIMULATOR modules. No real payment/provider integration or partial refunds are supported. '
            'For explicitly requested Razorpay TEST checkout use razorpay_test_contract {version:1,mode:razorpay_test,currency:INR,refunds:admin_full_only}, PostgreSQL, INR catalogue plus order/identity contracts. Never combine simulator and provider or include credentials. Live payments, fulfillment and partial refunds are unsupported. Provider round-trip evidence requires an external test account. '
            'For carts and UNPAID orders add order_contract version 1 with explicit tax_basis_points, shipping_minor, discount_basis_points, reservation_seconds and policy_label. Never invent tax/shipping rules; use clarified business configuration. Reviewed checkout reserves stock but cannot collect payments or fulfill orders. '
            'Identity writes require session CSRF; use browser forms for successful account journeys, '
            'and HTTP GET /api/account status 401 for anonymous-denial assertions. Never put operator credentials in checks. '
            'For this small local demo use the fewest necessary files. No login means auth_provider=None and auth_required=false. '
            'Use plain CSS; the offline runtime has no Tailwind dependency. '
            'Testing dependencies available: pytest, httpx, Playwright; avoid additional libraries. '
            'Preserve agreed API paths and UI selectors across sections. API create calls can use deterministic initial IDs in a fresh database. '
            'Browser tests start with a fresh database; for requested CRUD workflows assert visible creation, edit and deletion results. '
            'Journeys run in declared order against ONE shared database; a new browser page does not reset records or undo edits. '
            'After deleting a record, assert that the SAME record selector is hidden, never visible. '
            'Before deletion assert that the target exists, so deletion cannot pass by targeting an already absent record. '
            'Every POST/PUT/PATCH success check MUST include json with valid request data. '
            'Omit body_contains for 204 responses. If used, body_contains must contain meaningful expected response values, not {} or []. '
            'Every browser journey MUST finish with visible, text or hidden assertion AFTER the last click/fill. '
            'Use .note-item:first-child, not .note-item[0]. '
            'Use body_contains as a nonempty JSON object or list subset matching the actual response shape. '
            'NEVER put JSON Schema type/properties/items definitions inside body_contains. '
            'For POST with json={"title":"Test Note","body":"Hello"}, use body_contains={"title":"Test Note","body":"Hello"}, not an array or schema. '
            'All file paths are relative: frontend/src/App.tsx, NEVER /src/App.tsx. '
            'File dependencies contain only other declared file paths, NEVER package names. '
            'These are GENERATION dependencies: order the file list so dependencies refer only to earlier files. '
            'Never create self-dependencies or dependency cycles; configuration files need no source-file dependencies. '
            'The platform supplies platform_startup_files. You may return an empty files_to_create list when those files suffice. '
            'Declare only necessary additional files, such as styles or extracted modules. '
            'The files section must include backend/app/main.py and backend/app/__init__.py as well as all startup files listed above.')
        def section_lint(output):
            if name not in ('files', 'checks'):
                return []
            if name == 'files':
                try:
                    output.files_to_create = runtime_manifest(output.files_to_create,
                        generated.get('project_type', 'FULLSTACK_WEB'), [r.id for r in requirements])
                except ValueError as exc:
                    return [str(exc)]
            values = {**generated, **output.model_dump(mode='json', exclude_none=True, by_alias=True)}
            candidate = BuildSpec(project_id=context.project_id, project_name=context.project_name,
                requirements=requirements, generation_mode='MODEL', **values)
            if generated.get('source_generation_strategy') == 'RAZORPAY_TEST':
                from app.execution.agent.razorpay import prepare_spec
                candidate = prepare_spec(candidate)
                if name == 'files':output.files_to_create=candidate.files_to_create
            elif generated.get('source_generation_strategy') == 'PAYMENT_SIMULATOR':
                from app.execution.agent.payments import prepare_spec
                candidate = prepare_spec(candidate)
                if name == 'files':output.files_to_create=candidate.files_to_create
            elif generated.get('source_generation_strategy') == 'ORDERS':
                from app.execution.agent.orders import prepare_spec
                candidate = prepare_spec(candidate)
                if name == 'files':output.files_to_create=candidate.files_to_create
            elif generated.get('source_generation_strategy') == 'IDENTITY':
                from app.execution.agent.identity import prepare_spec
                candidate = prepare_spec(candidate)
                if name == 'files':
                    output.files_to_create = candidate.files_to_create
            elif generated.get('source_generation_strategy') == 'RELATIONAL_CRUD':
                from app.execution.agent.relational import prepare_spec
                candidate = prepare_spec(candidate)
                if name == 'files':
                    output.files_to_create = candidate.files_to_create
            elif generated.get('source_generation_strategy') == 'CATALOGUE':
                from app.execution.agent.catalogue import prepare_spec
                candidate = prepare_spec(candidate)
                if name == 'files':
                    output.files_to_create = candidate.files_to_create
            errors = validate(candidate, context)
            if name == 'files':
                return file_section_errors(errors)
            return errors
        result = await AgentExecutionHarness(target_schema=section_schema,
            agent_name='BuildSpec/' + name, system_prompt=instructions,
            llm_client=partial(llm_client, output_tokens=2048),
            extra_lint_rules=[section_lint]).execute(section_context, max_retries=1)
        if not result.success:
            raise RuntimeError(f'Build spec section {name} failed: {result.validation_errors + result.lint_violations}')
        generated.update(result.output.model_dump(mode='json', exclude_none=True, by_alias=True))
        if name == 'architecture' and generated.get('razorpay_test_contract'):
            generated['source_generation_strategy']='RAZORPAY_TEST'
        elif name == 'architecture' and generated.get('payment_simulation_contract'):
            generated['source_generation_strategy']='PAYMENT_SIMULATOR'
        elif name == 'architecture' and generated.get('order_contract'):
            generated['source_generation_strategy']='ORDERS'
        elif name == 'architecture' and generated.get('identity_contract'):
            generated['source_generation_strategy'] = 'IDENTITY'
        elif name == 'architecture' and generated.get('catalogue_contract'):
            generated['source_generation_strategy'] = 'CATALOGUE'
        elif name == 'architecture' and len(generated.get('database_entities', [])) > 1:
            generated['source_generation_strategy'] = 'RELATIONAL_CRUD'
    spec = BuildSpec(project_id=context.project_id, project_name=context.project_name,
        version=context.version, generation_mode='MODEL', overall_confidence=0,
        requirements=requirements, constraints=[c.description for c in context.constraints],
        assumptions=[copy_requirement(item) for item in context.assumptions], **generated)
    from app.config import get_settings
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
    elif spec.source_generation_strategy == 'RELATIONAL_CRUD':
        from app.execution.agent.relational import prepare_spec
        spec = prepare_spec(spec)
    elif get_settings().LOCAL_CODE_GENERATION_STRATEGY == 'declarative_crud':
        spec.source_generation_strategy = 'DECLARATIVE_CRUD'
        from app.execution.agent.declarative import validate_scope
        validate_scope(spec)
    errors = validate(spec, context)
    if errors:
        raise RuntimeError('Combined build spec validation failed: ' + '; '.join(errors))
    return spec


def file_section_errors(errors):
    return [e for e in errors if any(term in e.lower() for term in
            ('source path', 'startup files', 'file graph', 'dependencies', 'cycle'))]
