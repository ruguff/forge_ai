"""Phase 3 gate: real PostgreSQL, independent browser checks and rendered evidence."""
import base64
import hashlib
import json
from pathlib import Path
from app.execution.agent.catalogue import prepare_spec
from app.execution.orchestrator.coding_orchestrator import CodingOrchestrator
from app.execution.sandbox.catalogue_acceptance import (CONTRACT_VERSION,api_cases,browser_journeys,POSTGRES_TEST,RENDERED_TEST)
from app.execution.sandbox.result_parser import ResultParser
from app.execution.spec.catalogue_example import example_spec


def main():
    evidence=Path(__file__).resolve().parent.parent/'docs/ecommerce-evidence'
    root=evidence/'catalogue-app'
    spec=example_spec()
    # Acceptance values are frozen before source generation and never copied into
    # implementation context by the reviewed module.
    spec.acceptance_checks=api_cases()
    spec.browser_checks=browser_journeys()
    spec=prepare_spec(spec)
    evidence.mkdir(parents=True,exist_ok=True)
    (evidence/'catalogue-build-spec.json').write_text(spec.model_dump_json(indent=2),encoding='utf-8')
    orchestrator=CodingOrchestrator(root)
    build=orchestrator.execute_build(spec)
    report={'contract_version':CONTRACT_VERSION,'build':build.model_dump(mode='json'),
        'functional':'PENDING','security':'UNVERIFIED','accessibility':'TARGETED_CHECKS_PENDING',
        'performance':'UNVERIFIED','provider_integration':'NOT_IMPLEMENTED','screenshots':[]}
    for name,source in [('postgresql',POSTGRES_TEST),('rendered',RENDERED_TEST)]:
        path=root/'.projectforge'/('test_catalogue_'+name+'.py')
        path.write_text(source,encoding='utf-8')
        execution=orchestrator.test_runner.executor.execute('python -m pytest /source/.projectforge/'+path.name+' -v -s --no-header -p no:cacheprovider',timeout_sec=120)
        output=[]
        for line in execution.stdout.splitlines():
            if 'CATALOGUE_SCREENSHOT:' in line:
                payload=line.split('CATALOGUE_SCREENSHOT:',1)[1]
                name_key,encoded=payload.split(':',1)
                if name_key not in ('desktop-catalogue','mobile-catalogue','mobile-detail'):
                    raise ValueError('Unexpected screenshot name')
                png=base64.b64decode(encoded,validate=True)
                if not png.startswith(b'\x89PNG\r\n\x1a\n') or len(png)>1_500_000:
                    raise ValueError('Invalid or oversized screenshot')
                target=evidence/('catalogue-'+name_key+'.png')
                target.write_bytes(png)
                report['screenshots'].append({'path':str(target),'sha256':hashlib.sha256(png).hexdigest()})
            else:output.append(line)
        result=ResultParser.parse_pytest('\n'.join(output),execution.stderr,execution.exit_code,execution.duration_ms)
        report[name]=result.model_dump(mode='json')
        (evidence/'catalogue-verification.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
        print(name+': '+('PASSED' if result.is_success else 'FAILED'),flush=True)
    report['functional']='PASSED' if build.status=='VERIFIED' and report['postgresql']['exit_code']==0 and report['rendered']['exit_code']==0 else 'FAILED'
    report['accessibility']='TARGETED_KEYBOARD_AND_LAYOUT_PASSED' if report['rendered']['exit_code']==0 else 'FAILED'
    (evidence/'catalogue-verification.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    assert report['functional']=='PASSED','See docs/ecommerce-evidence/catalogue-verification.json'
    assert len(report['screenshots'])==3,'Missing rendered evidence'
    print('Catalogue API, PostgreSQL restart/constraints, browser and desktop/mobile checks passed.')


if __name__=='__main__':main()
