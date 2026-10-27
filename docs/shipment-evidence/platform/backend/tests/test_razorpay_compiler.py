"""Provider mode remains test-only and cannot claim real integration from mocks."""
import json
from types import SimpleNamespace
import pytest
from pydantic import ValidationError
from tests.test_orders_compiler import spec as order_spec
from app.execution.agent.razorpay import prepare_spec,sources,validate_scope
from app.execution.spec.razorpay_contract import RazorpayTestContract
from app.execution.spec.payment_contract import PaymentSimulationContract

def spec():
    value=order_spec();value.razorpay_test_contract=RazorpayTestContract();return value

def test_source_contract_and_prior_migrations_preserved():
    from app.execution.agent.orders import sources as previous
    after=sources(prepare_spec(spec()));before=previous(order_spec())
    assert len(after)==48
    assert 'backend/app/fulfillment_runtime.py' in after
    assert 'frontend/src/Fulfillment.tsx' in after
    assert any(e.path=='/api/orders/{order_id}/shipment' and e.auth_required for e in prepare_spec(spec()).api_endpoints)
    assert 'ShipmentTracking' in after['frontend/src/App.tsx']
    assert '.shipment-timeline' in after['frontend/src/identity.css']
    assert json.loads(after['frontend/src/ui-contract.json'])['delivery']['version']==3
    assert any(e.path=='/api/admin/orders/{order_id}/shipping-details' and e.auth_required for e in prepare_spec(spec()).api_endpoints)
    for revision in ('0001','0002','0003'):
        assert before['backend/migrations/'+revision+'.json']==after['backend/migrations/'+revision+'.json']
    assert json.loads(after['backend/migrations/0004_razorpay_test.json'])['parent']=='0003'
    assert 'backend/app/payment_runtime.py' not in after
    assert 'RAZORPAY TEST MODE' in after['frontend/src/RazorpayCheckout.tsx']
    assert 'FAKE_SOURCE' not in '\n'.join(after.values())
    for path,value in after.items():
        if path.endswith('.py'):compile(value,path,'exec')
    from app.execution.sandbox.razorpay_gate import SOURCE
    compile(SOURCE,'provider contract','exec')
    from app.execution.sandbox.razorpay_browser import SOURCE
    compile(SOURCE,'provider browser','exec')

@pytest.mark.parametrize('fields',[{'mode':'live'},{'currency':'USD'},{'secret':'never-accepted'},{'refunds':'partial'}])
def test_contract_rejects_live_secrets_and_expanded_scope(fields):
    with pytest.raises(ValidationError):RazorpayTestContract(**fields)

def test_simulation_and_provider_are_mutually_exclusive():
    value=spec();value.payment_simulation_contract=PaymentSimulationContract()
    with pytest.raises(ValueError,match='excludes the simulator'):validate_scope(value)

@pytest.mark.asyncio
async def test_bounded_compiler_keeps_checks_and_provider_contract():
    from app.models.schemas import ProjectContext,ExtractedRequirementItem,RequirementSource,RequirementType
    from app.execution.spec.local_compiler import compile_local
    from app.execution.spec.model_compiler import validate_spec
    context=ProjectContext(project_id='RZP-SECTIONS',raw_request='Razorpay TEST checkout',requirements=[ExtractedRequirementItem(id='CAT-001',dimension='functional',title='Test payments',description='Razorpay TEST checkout',type=RequirementType.EXPLICIT,source=RequirementSource.USER,confidence=1,evidence='User')])
    empty=SimpleNamespace(model_dump=lambda **kwargs:{})
    state=SimpleNamespace(engineering_spec=empty,ai_spec=empty,ux_spec=empty,security_report=empty,qa_spec=SimpleNamespace(critical_test_cases=[]))
    values=spec().model_dump(mode='json');values['catalogue_contract']['products']=values['catalogue_contract']['products'][:2]
    checks=[{'method':'GET','path':'/api/account','status':401,'requirements':['CAT-001']}]
    journeys=[{'name':'Account','requirements':['CAT-001'],'steps':[{'action':'goto','path':'/account'},{'action':'visible','selector':'[data-testid="identity-submit"]'}]}]
    sections=[{k:values[k] for k in ('project_type','tech_stack','database_entities','api_endpoints','catalogue_contract','identity_contract','order_contract','razorpay_test_contract')},{},{'acceptance_checks':checks,'browser_checks':journeys},{}];calls=[]
    async def generate(prompt,*,output_tokens):
        assert output_tokens==2048;calls.append(prompt);return json.dumps(sections[len(calls)-1])
    result=await compile_local(context,state,generate,'Compile',validate_spec)
    assert result.source_generation_strategy=='RAZORPAY_TEST' and len(calls)==4
    assert result.acceptance_checks==checks and result.browser_checks==journeys
    assert len(result.files_to_create)==48

@pytest.mark.parametrize('failed_gate',[None,'run_razorpay_checks','run_razorpay_browser_checks'])
def test_mock_success_never_claims_provider_verification(tmp_path,monkeypatch,failed_gate):
    from app.execution.orchestrator.coding_orchestrator import CodingOrchestrator
    from app.execution.sandbox.result_parser import ResultParser
    from app.execution.sandbox.executor import ExecutionResult
    value=prepare_spec(spec());value.acceptance_checks=[{'method':'GET','path':'/api/store','status':200}];value.browser_checks=[{'steps':[{'action':'visible','selector':'h1'}]}]
    orchestrator=CodingOrchestrator(tmp_path);runner=orchestrator.test_runner;passed=ResultParser.parse_pytest('1 passed','',0)
    monkeypatch.setattr(runner.executor,'preflight',lambda:(True,'test double'))
    monkeypatch.setattr(runner,'run_frontend_build',lambda:ExecutionResult(command='build',exit_code=0,stdout='',stderr='',duration_ms=1))
    for method in ('run_backend_tests','run_acceptance','run_browser_checks','run_identity_checks','run_order_checks','run_order_browser_checks','run_razorpay_checks','run_razorpay_browser_checks'):
        monkeypatch.setattr(runner,method,lambda *args:passed)
    if failed_gate:monkeypatch.setattr(runner,failed_gate,lambda:ResultParser.parse_pytest('1 failed','',1))
    report=orchestrator.execute_build(value)
    assert report.tests_passed and report.status=='REQUIRES_HUMAN'
    assert report.verification_checks['razorpay_provider_integration']=='UNVERIFIED'
    if failed_gate:assert 'FAILED' in report.verification_checks.values()
    else:assert all(v=='PASSED' for k,v in report.verification_checks.items() if k!='razorpay_provider_integration')
