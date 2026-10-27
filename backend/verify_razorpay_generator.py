"""Phase 7 local verification only; provider integration deliberately remains unverified."""
import base64,json,hashlib
from pathlib import Path
from app.execution.agent.razorpay import prepare_spec
from app.execution.spec.razorpay_contract import RazorpayTestContract
from app.execution.spec.identity_contract import IdentityContract
from app.execution.spec.order_contract import OrderContract
from app.execution.spec.catalogue_example import example_spec
from app.execution.sandbox.catalogue_acceptance import api_cases,browser_journeys
from app.execution.orchestrator.coding_orchestrator import CodingOrchestrator

def main():
    evidence=Path(__file__).resolve().parent.parent/'docs/ecommerce-evidence';root=evidence/'razorpay-app'
    spec=example_spec();spec.project_id='RAZORPAY-TEST-DEMO';spec.project_name='Fieldwork Razorpay test fixture'
    spec.identity_contract=IdentityContract(public_origin='http://127.0.0.1:3001',allow_local_http=True)
    spec.tech_stack.auth_provider='session'
    spec.order_contract=OrderContract(tax_basis_points=500,shipping_minor=500,discount_basis_points=0,reservation_seconds=900,policy_label='Synthetic verification rules')
    spec.razorpay_test_contract=RazorpayTestContract()
    spec.acceptance_checks=api_cases();spec.acceptance_checks[0]['body_contains']['capabilities']['checkout']=True
    spec.browser_checks=browser_journeys();spec=prepare_spec(spec)
    evidence.mkdir(parents=True,exist_ok=True)
    (evidence/'razorpay-build-spec.json').write_text(spec.model_dump_json(indent=2),encoding='utf-8')
    orchestrator=CodingOrchestrator(root);build=orchestrator.execute_build(spec)
    local=all(v=='PASSED' for k,v in build.verification_checks.items() if k!='razorpay_provider_integration')
    report={'scope':'Razorpay TEST adapter; synthetic upstream API and mocked Checkout only','build':build.model_dump(mode='json'),
        'local_functional':'PASSED' if local else 'FAILED','provider_integration':'UNVERIFIED_NO_TEST_ACCOUNT',
        'security':'TARGETED_ONLY','accessibility':'TARGETED_KEYBOARD_AND_LAYOUT_ONLY','performance':'UNVERIFIED','production_ready':False,'screenshots':[]}
    target=evidence/'razorpay-verification.json'
    target.write_text(json.dumps(report,indent=2),encoding='utf-8')
    print('Build:',build.status,'Checks:',build.verification_checks,flush=True)
    assert local and build.status=='REQUIRES_HUMAN','Local verification failed; see saved report'
    marker=root/'.projectforge/capture_payment_screenshots';marker.write_text('Local screenshots, mocked provider',encoding='utf-8')
    try:visual=orchestrator.test_runner.run_razorpay_browser_checks()
    finally:marker.unlink(missing_ok=True)
    for line in visual.raw_stdout.splitlines():
        if 'RAZORPAY_SCREENSHOT:' not in line:continue
        label,data=line.split('RAZORPAY_SCREENSHOT:',1)[1].split(':',1)
        assert label in ('desktop','mobile')
        image=base64.b64decode(data.strip(),validate=True);assert image.startswith(b'\x89PNG') and len(image)<1500000
        image_path=evidence/('razorpay-'+label+'.png');image_path.write_bytes(image)
        report['screenshots'].append({'path':str(image_path),'sha256':hashlib.sha256(image).hexdigest(),'label':label})
    report['visual_browser']=visual.model_dump(mode='json');report['visual_inspection']='PENDING'
    target.write_text(json.dumps(report,indent=2),encoding='utf-8')
    assert visual.is_success and len(report['screenshots'])==2,'Visual browser check failed'
    print('Local checks and screenshots passed. Real provider integration remains unverified.',flush=True)

if __name__=='__main__':main()
