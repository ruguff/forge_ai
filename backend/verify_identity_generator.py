"""Independent phase-4 PostgreSQL and browser evidence, no live credentials."""
import base64,json,hashlib
from pathlib import Path
from app.execution.spec.catalogue_example import example_spec
from app.execution.spec.identity_contract import IdentityContract
from app.execution.agent.identity import prepare_spec
from app.execution.orchestrator.coding_orchestrator import CodingOrchestrator
from app.execution.sandbox.catalogue_acceptance import api_cases,browser_journeys
from app.execution.sandbox.identity_acceptance import POSTGRES_TEST,BROWSER_TEST

def main():
    evidence=Path(__file__).resolve().parent.parent/'docs/ecommerce-evidence';root=evidence/'identity-app'
    spec=example_spec();spec.identity_contract=IdentityContract(public_origin='http://127.0.0.1:3001',allow_local_http=True)
    spec.tech_stack.auth_provider='session';spec.project_id='IDENTITY-DEMO'
    spec.acceptance_checks=api_cases();spec.browser_checks=browser_journeys();spec=prepare_spec(spec)
    evidence.mkdir(parents=True,exist_ok=True)
    (evidence/'identity-build-spec.json').write_text(spec.model_dump_json(indent=2),encoding='utf-8')
    orchestrator=CodingOrchestrator(root);build=orchestrator.execute_build(spec)
    report={'contract_version':1,'build':build.model_dump(mode='json'),'functional':'PENDING','security':'TARGETED_CHECKS_PENDING','accessibility':'TARGETED_CHECKS_PENDING','performance':'UNVERIFIED','smtp_delivery':'UNVERIFIED','provider_integration':'NOT_IMPLEMENTED','screenshots':[]}
    for key,source in [('postgresql',POSTGRES_TEST),('browser',BROWSER_TEST)]:
        path=root/'.projectforge'/('test_identity_'+key+'.py');path.write_text(source,encoding='utf-8')
        execution=orchestrator.test_runner.executor.execute('python -m pytest /source/.projectforge/'+path.name+' -v -s --no-header -p no:cacheprovider',timeout_sec=120)
        lines=[]
        for line in execution.stdout.splitlines():
            if 'IDENTITY_SCREENSHOT:' in line:
                label,encoded=line.split('IDENTITY_SCREENSHOT:',1)[1].split(':',1)
                if label not in ('desktop-account','mobile-account','desktop-admin','mobile-admin'):raise ValueError('Unexpected evidence label')
                png=base64.b64decode(encoded,validate=True)
                if not png.startswith(b'\x89PNG\r\n\x1a\n') or len(png)>1500000:raise ValueError('Invalid image')
                target=evidence/('identity-'+label+'.png');target.write_bytes(png)
                report['screenshots'].append({'path':str(target),'sha256':hashlib.sha256(png).hexdigest()})
            else:lines.append(line)
        report[key]={**execution.model_dump(mode='json'),'stdout':'\n'.join(lines)}
        (evidence/'identity-verification.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
        print(key+': '+str(execution.exit_code),flush=True)
    success=build.status=='VERIFIED' and all(report[k]['exit_code']==0 for k in ('postgresql','browser')) and len(report['screenshots'])==4
    report['functional']='PASSED' if success else 'FAILED'
    report['security']='TARGETED_IDENTITY_CHECKS_PASSED' if report['postgresql']['exit_code']==0 else 'FAILED'
    report['accessibility']='TARGETED_KEYBOARD_LAYOUT_PASSED' if report['browser']['exit_code']==0 else 'FAILED'
    (evidence/'identity-verification.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    assert success,'Inspect identity-verification.json; no assertions were weakened'
if __name__=='__main__':main()
