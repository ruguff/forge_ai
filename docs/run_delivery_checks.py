"""Run copies of the demos in network-disabled disposable PostgreSQL containers."""
import sys,json,shutil,base64,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'backend'))
from app.execution.sandbox.test_runner import TestRunner
from app.execution.sandbox.fulfillment_gate import SOURCE,BROWSER
from app.execution.sandbox.razorpay_gate import SOURCE as RAZORPAY
RAZORPAY += '''

def test_test_provider_delivery_and_refund_exclusion():
    c,aid=buyer();o=order(c,aid);a=operator();oid=start(c,o);pid=gateway.pay(oid)
    path=f"/api/admin/orders/{o['id']}/fulfillment"
    body={'expected_status':'not_packed','status':'packed'}
    assert post(a,path,body).status_code==409
    assert post(c,endpoint(o,'verify'),callback(oid,pid)).status_code==200
    before=stock('PACK-OLIVE-18')
    assert post(c,path,body).status_code==403
    assert post(a,path,body).json()['status']=='packed'
    assert post(a,endpoint(o,'refund',True),{'idempotency_key':secrets.token_hex(16)}).status_code==409
    assert stock('PACK-OLIVE-18')==before
    for previous,next_status in [('packed','shipped'),('shipped','delivered')]:
        assert post(a,path,{'expected_status':previous,'status':next_status}).json()['status']==next_status
    assert c.get('/api/orders/'+str(o['id'])).json()['fulfillment']['status']=='delivered'
'''
dest=ROOT/'docs/delivery-evidence'
dest.mkdir(exist_ok=True)
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
    report['controls']=runner._payment_gate('delivery_controls',SOURCE if name=='payments-app' else RAZORPAY).model_dump()
    (dest/(name+'-results.json')).write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(name,'controls',report['controls']['passed_count'],report['controls']['failed_count'],flush=True)
    report['frontend_build']=runner.run_frontend_build().model_dump()
    if name=='payments-app':
        (stage/'.projectforge/capture_payment_screenshots').touch()
        report['browser']=runner._payment_gate('delivery_browser',BROWSER).model_dump()
        for kind,data in re.findall(r'DELIVERY_(DESKTOP|MOBILE)_PNG=([A-Za-z0-9+/=]+)',report['browser']['raw_stdout']):
            (dest/(kind.lower()+'.png')).write_bytes(base64.b64decode(data))
        report['browser']['raw_stdout']=re.sub(r'DELIVERY_(DESKTOP|MOBILE)_PNG=[A-Za-z0-9+/=]+','[Screenshot saved]',report['browser']['raw_stdout'])
        print(name,'browser',report['browser']['passed_count'],report['browser']['failed_count'],flush=True)
    (dest/(name+'-results.json')).write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(name,'build',report['frontend_build']['exit_code'],flush=True)
