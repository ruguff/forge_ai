import pytest
from types import SimpleNamespace
from app.models.schemas import ProjectContext, ExtractedRequirementItem, RequirementSource, RequirementType
from app.execution.spec.local_compiler import copy_requirement, compile_local
from app.execution.spec.model_compiler import validate_spec


def test_cycle_is_rejected_in_file_section_before_checks():
    from app.execution.spec.local_compiler import file_section_errors, HttpCheck
    assert file_section_errors(['Cycle detected in task graph', 'Acceptance checks absent']) == ['Cycle detected in task graph']
    check = HttpCheck.model_validate({'method': 'POST', 'path': '/api/notes', 'status': 201,
        'json': {'title': 'Test'}, 'requirements': ['REQ-1']})
    assert check.model_dump(by_alias=True)['json'] == {'title': 'Test'}


@pytest.mark.parametrize('source,expected', [(RequirementSource.USER, 'USER'), (RequirementSource.INFERENCE, 'INFERRED'), (RequirementSource.AGENT, 'AGENT')])
def test_requirement_copy_preserves_identity_and_provenance(source, expected):
    item = ExtractedRequirementItem(id='REQ-ORIGINAL', dimension='functional', title='Save',
        description='Persist across restarts', type=RequirementType.EXPLICIT,
        source=source, confidence=0.7, evidence='Original evidence')
    result = copy_requirement(item)
    assert (result.id, result.description, result.source.value) == (item.id, item.description, expected)
    assert result.confidence == item.confidence


@pytest.mark.asyncio
async def test_section_compiler_cannot_accept_missing_files_or_checks():
    context = ProjectContext(project_id='PROJ-SECTION-TEST', raw_request='Notes')
    empty = SimpleNamespace(model_dump=lambda **kwargs: {})
    state = SimpleNamespace(engineering_spec=empty, ai_spec=empty, ux_spec=empty,
                            security_report=empty, qa_spec=SimpleNamespace(critical_test_cases=[]))
    calls = []
    async def generate(prompt, *, output_tokens):
        calls.append(prompt)
        return '{}'
    with pytest.raises(RuntimeError, match='Build spec section checks failed'):
        await compile_local(context, state, generate, 'Compile notes', validate_spec)
    assert len(calls) == 4  # Architecture and files, then checks and one bounded retry.


def test_platform_manifest_is_complete_without_source_templates():
    from app.execution.spec.local_compiler import runtime_manifest
    from app.execution.spec.build_spec_models import BuildSpec
    from app.execution.tasks.task_graph import TaskGraph
    files = runtime_manifest([], 'FULLSTACK_WEB', ['REQ-ORIGINAL'])
    assert 'frontend/src/App.tsx' in {item.file_path for item in files}
    assert 'backend/requirements.txt' in {item.file_path for item in files}
    assert all(item.traceable_requirements == ['REQ-ORIGINAL'] for item in files)
    spec = BuildSpec(project_id='PROJ-MANIFEST', project_name='Demo', generation_mode='MODEL', files_to_create=files)
    TaskGraph().build_from_spec(spec)  # The platform's own generation graph is acyclic.
    backend_files = runtime_manifest([], 'BACKEND_API', ['REQ-ORIGINAL'])
    assert not any(item.file_path.startswith('frontend/') for item in backend_files)


@pytest.mark.asyncio
async def test_local_sections_select_reviewed_relational_runtime():
    import json
    from tests.test_relational import related_spec
    context = ProjectContext(project_id='RELATIONAL-SECTIONS', raw_request='Manage categories and products',
        requirements=[ExtractedRequirementItem(id='REQ-1',dimension='functional',title='Related records',
            description='Create and manage categories and products',type=RequirementType.EXPLICIT,
            source=RequirementSource.USER, confidence=1,evidence='User request')])
    empty = SimpleNamespace(model_dump=lambda **kwargs: {})
    state = SimpleNamespace(engineering_spec=empty, ai_spec=empty, ux_spec=empty, security_report=empty,
        qa_spec=SimpleNamespace(critical_test_cases=[]))
    spec = related_spec('PostgreSQL').model_dump(mode='json')
    sections = [
        {key:spec[key] for key in ('project_type','tech_stack','database_entities','api_endpoints','relational_contract')},
        {},
        {'acceptance_checks':[{'method':'GET','path':'/api/categories','status':200,'requirements':['REQ-1']}],
         'browser_checks':[{'name':'Entity navigation','requirements':['REQ-1'],'steps':[
             {'action':'text','selector':'nav','value':'Category'}]}]},
        {}]
    calls = []
    async def generate(prompt, *, output_tokens):
        assert output_tokens == 2048
        calls.append(prompt)
        return json.dumps(sections[len(calls)-1])
    result = await compile_local(context,state,generate,'Compile',validate_spec)
    assert len(calls) == 4
    assert result.source_generation_strategy == 'RELATIONAL_CRUD'
    assert result.tech_stack.primary_database == 'PostgreSQL'
    assert 'backend/app/relational_runtime.py' in {f.file_path for f in result.files_to_create}
    assert result.acceptance_checks[0]['path'] == '/api/categories'


@pytest.mark.asyncio
async def test_local_sections_preserve_catalogue_contract_and_assertions():
    import json
    from app.execution.spec.catalogue_example import example_spec
    context=ProjectContext(project_id='CATALOGUE-SECTIONS',raw_request='Build a public read-only product catalogue',
        requirements=[ExtractedRequirementItem(id='CAT-001',dimension='functional',title='Browse catalogue',
            description='Browse categories, products and variants with search and filters',type=RequirementType.EXPLICIT,
            source=RequirementSource.USER,confidence=1,evidence='User request')])
    empty=SimpleNamespace(model_dump=lambda **kwargs:{})
    state=SimpleNamespace(engineering_spec=empty,ai_spec=empty,ux_spec=empty,security_report=empty,
        qa_spec=SimpleNamespace(critical_test_cases=[]))
    spec=example_spec().model_dump(mode='json')
    # Keep the model fixture as small as the bounded architecture prompt requests.
    spec['catalogue_contract']['products']=spec['catalogue_contract']['products'][:2]
    frozen_checks=[{'method':'GET','path':'/api/products','status':200,'body_contains':{'total':2},'requirements':['CAT-001']}]
    frozen_browser=[{'name':'Small catalogue','requirements':['CAT-001'],'steps':[
        {'action':'text','selector':'[data-testid="catalogue-results"]','value':'2 essentials'},
        {'action':'click','selector':'[data-testid="catalogue-product"][data-product-slug="trail-pack"] a'},
        {'action':'select','selector':'[data-testid="catalogue-variant"]','value':'PACK-SAND-18'},
        {'action':'text','selector':'[data-testid="catalogue-availability"]','value':'Out of stock'}]}]
    sections=[{key:spec[key] for key in ('project_type','tech_stack','database_entities','api_endpoints','catalogue_contract')},
        {},{'acceptance_checks':frozen_checks,'browser_checks':frozen_browser},{}]
    calls=[]
    async def generate(prompt,*,output_tokens):
        assert output_tokens==2048
        calls.append(prompt)
        return json.dumps(sections[len(calls)-1])
    result=await compile_local(context,state,generate,'Compile',validate_spec)
    assert len(calls)==4
    assert result.source_generation_strategy=='CATALOGUE'
    assert result.catalogue_contract.products[0].slug=='trail-pack'
    assert result.acceptance_checks==frozen_checks
    assert result.browser_checks==frozen_browser
    assert 'frontend/src/ui-contract.json' in {f.file_path for f in result.files_to_create}


@pytest.mark.asyncio
async def test_bounded_identity_compiler_preserves_frozen_assertions():
    import json
    from app.execution.spec.catalogue_example import example_spec
    from app.execution.spec.identity_contract import IdentityContract
    context=ProjectContext(project_id='IDENTITY-SECTIONS',raw_request='Catalogue with accounts and owned addresses',
        requirements=[ExtractedRequirementItem(id='CAT-001',dimension='functional',title='Accounts',
            description='Customer accounts and owned addresses',type=RequirementType.EXPLICIT,source=RequirementSource.USER,confidence=1,evidence='User')])
    empty=SimpleNamespace(model_dump=lambda **kwargs:{})
    state=SimpleNamespace(engineering_spec=empty,ai_spec=empty,ux_spec=empty,security_report=empty,qa_spec=SimpleNamespace(critical_test_cases=[]))
    spec=example_spec();spec.identity_contract=IdentityContract();spec.tech_stack.auth_provider='session'
    values=spec.model_dump(mode='json');values['catalogue_contract']['products']=values['catalogue_contract']['products'][:2]
    checks=[{'method':'GET','path':'/api/account','status':401,'requirements':['CAT-001']}]
    journeys=[{'name':'Sign in form','requirements':['CAT-001'],'steps':[{'action':'goto','path':'/account'},
        {'action':'visible','selector':'[data-testid="identity-submit"]'}]}]
    sections=[{key:values[key] for key in ('project_type','tech_stack','database_entities','api_endpoints','catalogue_contract','identity_contract')},
        {},{'acceptance_checks':checks,'browser_checks':journeys},{}]
    calls=[]
    async def generate(prompt,*,output_tokens):
        assert output_tokens==2048
        calls.append(prompt);return json.dumps(sections[len(calls)-1])
    result=await compile_local(context,state,generate,'Compile',validate_spec)
    assert len(calls)==4 and result.source_generation_strategy=='IDENTITY'
    assert result.acceptance_checks==checks and result.browser_checks==journeys
    assert 'backend/app/identity_runtime.py' in {f.file_path for f in result.files_to_create}
