"""Simulator boundaries and mandatory gates, independent of the generated app."""
import json
from types import SimpleNamespace
import pytest
from pydantic import ValidationError
from app.execution.agent.payments import prepare_spec, sources, validate_scope
from app.execution.spec.payment_contract import PaymentSimulationContract
from tests.test_orders_compiler import spec as order_spec


def spec():
    value=order_spec()
    value.payment_simulation_contract=PaymentSimulationContract()
    return value


def test_simulation_source_manifest_and_immutable_prior_migrations():
    from app.execution.agent.orders import sources as order_sources
    before=order_sources(order_spec());after=sources(prepare_spec(spec()))
    assert 'backend/app/fulfillment_runtime.py' in after
    assert 'frontend/src/Fulfillment.tsx' in after
    assert any(e.path=='/api/orders/{order_id}/shipment' and e.auth_required for e in prepare_spec(spec()).api_endpoints)
    assert 'ShipmentTracking' in after['frontend/src/App.tsx']
    assert '.shipment-timeline' in after['frontend/src/identity.css']
    assert json.loads(after['frontend/src/ui-contract.json'])['delivery']['version']==3
    assert any(e.path=='/api/admin/orders/{order_id}/shipping-details' and e.auth_required for e in prepare_spec(spec()).api_endpoints)
    for revision in ('0001','0002','0003'):
        assert before['backend/migrations/'+revision+'.json']==after['backend/migrations/'+revision+'.json']
    assert len(after)==46
    assert json.loads(after['backend/migrations/0004.json'])['parent']=='0003'
    assert 'OFFLINE PAYMENT SIMULATOR' in after['frontend/src/Payments.tsx']
    for path,source in after.items():
        if path.endswith('.py'):compile(source,path,'exec')
    from app.execution.sandbox.payment_gate import SOURCE
    compile(SOURCE,'payment gate','exec')
    from app.execution.sandbox.payment_browser import SOURCE
    compile(SOURCE,'payment browser','exec')


@pytest.mark.parametrize('fields',[{'mode':'live'},{'mode':'razorpay'},{'api_key':'never-accepted'},{'refunds':'partial'}])
def test_live_credentials_and_unsupported_contracts_rejected(fields):
    with pytest.raises(ValidationError):PaymentSimulationContract(**fields)


@pytest.mark.parametrize('description',['Integrate Razorpay','Collect real payments','Support partial refunds','Add fulfillment'])
def test_unsupported_payment_requirements_fail_closed(description):
    value=spec();value.requirements[0].description=description
    with pytest.raises(ValueError,match='exceeds offline simulator'):validate_scope(value)


@pytest.mark.asyncio
async def test_bounded_compiler_preserves_assertions_and_selects_simulator():
    from app.models.schemas import ProjectContext,ExtractedRequirementItem,RequirementSource,RequirementType
    from app.execution.spec.local_compiler import compile_local
    from app.execution.spec.model_compiler import validate_spec
    context=ProjectContext(project_id='SIM-SECTIONS',raw_request='Offline payment simulation for a store',requirements=[
        ExtractedRequirementItem(id='CAT-001',dimension='functional',title='Simulation',description='Offline payment simulation',type=RequirementType.EXPLICIT,source=RequirementSource.USER,confidence=1,evidence='User')])
    empty=SimpleNamespace(model_dump=lambda **kwargs:{})
    state=SimpleNamespace(engineering_spec=empty,ai_spec=empty,ux_spec=empty,security_report=empty,qa_spec=SimpleNamespace(critical_test_cases=[]))
    values=spec().model_dump(mode='json');values['catalogue_contract']['products']=values['catalogue_contract']['products'][:2]
    checks=[{'method':'GET','path':'/api/account','status':401,'requirements':['CAT-001']}]
    journeys=[{'name':'Sign in','requirements':['CAT-001'],'steps':[{'action':'goto','path':'/account'},{'action':'visible','selector':'[data-testid="identity-submit"]'}]}]
    sections=[{k:values[k] for k in ('project_type','tech_stack','database_entities','api_endpoints','catalogue_contract','identity_contract','order_contract','payment_simulation_contract')},{},{'acceptance_checks':checks,'browser_checks':journeys},{}]
    calls=[]
    async def generate(prompt,*,output_tokens):
        assert output_tokens==2048
        calls.append(prompt);return json.dumps(sections[len(calls)-1])
    result=await compile_local(context,state,generate,'Compile',validate_spec)
    assert result.source_generation_strategy=='PAYMENT_SIMULATOR' and len(calls)==4
    assert result.acceptance_checks==checks and result.browser_checks==journeys
    assert len(result.files_to_create)==46


@pytest.mark.parametrize('failed_gate',['run_payment_checks','run_payment_browser_checks'])
def test_payment_failure_prevents_verified_even_if_backend_passes(tmp_path,monkeypatch,failed_gate):
    from app.execution.orchestrator.coding_orchestrator import CodingOrchestrator
    from app.execution.sandbox.result_parser import ResultParser
    from app.execution.sandbox.executor import ExecutionResult
    value=prepare_spec(spec())
    value.acceptance_checks=[{'method':'GET','path':'/api/store','status':200}]
    value.browser_checks=[{'steps':[{'action':'visible','selector':'h1'}]}]
    orchestrator=CodingOrchestrator(tmp_path);runner=orchestrator.test_runner
    passed=ResultParser.parse_pytest('1 passed','',0)
    monkeypatch.setattr(runner.executor,'preflight',lambda:(True,'test double'))
    monkeypatch.setattr(runner,'run_frontend_build',lambda:ExecutionResult(command='build',exit_code=0,stdout='',stderr='',duration_ms=1))
    for method in ('run_backend_tests','run_acceptance','run_browser_checks','run_identity_checks','run_order_checks','run_order_browser_checks','run_payment_checks','run_payment_browser_checks'):
        monkeypatch.setattr(runner,method,lambda *args:passed)
    monkeypatch.setattr(runner,failed_gate,lambda:ResultParser.parse_pytest('1 failed','',1))
    report=orchestrator.execute_build(value)
    assert report.tests_passed and report.status=='REQUIRES_HUMAN'
    assert report.verification_checks['payment_simulation' if failed_gate=='run_payment_checks' else 'payment_simulation_browser']=='FAILED'
