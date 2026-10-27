"""Run copies of the demos in network-disabled disposable PostgreSQL containers."""
import sys,json,shutil,base64,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'backend'))
from app.execution.sandbox.test_runner import TestRunner
from app.execution.sandbox.customer_shipment_gate import BROWSER
dest=ROOT/'docs/shipment-evidence'
dest.mkdir(exist_ok=True)
failures=[]
for name in ('payments-app','razorpay-app'):
    if len(sys.argv)>1 and name!=sys.argv[1]:continue
    stage=dest/name;source=ROOT/'docs/ecommerce-evidence'/name
    for file in source.rglob('*'):
        relative=file.relative_to(source)
        if set(relative.parts)&{'.venv','node_modules','__pycache__','.git','.projectforge','dist','.vite-cache'} or file.is_symlink():continue
        if file.is_file() and file.suffix in {'.py','.json','.ts','.tsx','.css','.html','.svg'} and not file.name.startswith('.env'):
            target=stage/relative;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(file,target)
    runner=TestRunner(stage)
    runner.executor.docker=r'C:\Users\HET\AppData\Local\Programs\DockerDesktop\resources\bin\docker.exe'
    runner.executor.image='projectforge-relational-runtime:local'
    report={}
    report['controls']=(runner.run_payment_checks() if name=='payments-app' else runner.run_razorpay_checks()).model_dump()
    (dest/(name+'-results.json')).write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(name,'controls',report['controls']['passed_count'],report['controls']['failed_count'],flush=True)
    report['frontend_build']=runner.run_frontend_build().model_dump()
    if name=='payments-app':
        (stage/'.projectforge/capture_payment_screenshots').touch()
        report['browser']=runner._payment_gate('shipment_browser',BROWSER).model_dump()
        for kind,data in re.findall(r'(?:DELIVERY|TRACKING|SHIPMENT)_(DESKTOP|MOBILE|FORM_DESKTOP|FORM_MOBILE|CUSTOMER)_PNG=([A-Za-z0-9+/=]+)',report['browser']['raw_stdout']):
            (dest/('capture-'+kind.lower()+'.png')).write_bytes(base64.b64decode(data))
        report['browser']['raw_stdout']=re.sub(r'(?:DELIVERY|TRACKING|SHIPMENT)_(DESKTOP|MOBILE|FORM_DESKTOP|FORM_MOBILE|CUSTOMER)_PNG=[A-Za-z0-9+/=]+','[Screenshot saved]',report['browser']['raw_stdout'])
        print(name,'browser',report['browser']['passed_count'],report['browser']['failed_count'],flush=True)
    (dest/(name+'-results.json')).write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(name,'build',report['frontend_build']['exit_code'],flush=True)

    for check,result in report.items():
        if result.get('exit_code')!=0 or result.get('failed_count',0) or result.get('error_count',0):failures.append(name+': '+check)
print('Failed checks:', failures)
sys.exit(bool(failures))
