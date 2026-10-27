"""Bounded synthetic tests in the existing network-disabled disposable sandbox."""
import json, shutil, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'backend'))
from app.execution.sandbox.test_runner import TestRunner
from app.execution.sandbox.razorpay_gate import SOURCE

DEST = Path(__file__).parent
stage = DEST / 'isolated-app'
source = ROOT / 'docs/ecommerce-evidence/razorpay-app'
# Explicit source allowlist: never copy environment files, installed packages or databases.
for directory, suffixes in [('backend/app', {'.py', '.json'}), ('backend/migrations', {'.json'})]:
    for file in (source / directory).rglob('*'):
        if file.is_file() and not file.is_symlink() and file.suffix in suffixes:
            target = stage / file.relative_to(source)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(file, target)

prefix = SOURCE.split('def test_unconfigured_live_guard_and_authority():')[0]
tests = r'''
def test_reset_shared_bucket_denies_a_different_victim():
    from app.identity_runtime import digest
    victim, _ = buyer()
    token=secrets.token_urlsafe(32)
    with app.state.engine.begin() as db:
        uid=db.execute(text('SELECT id FROM users ORDER BY id DESC LIMIT 1')).scalar_one()
        db.execute(text('INSERT INTO password_resets (token_hash,user_id,expires_at,used) VALUES (:token,:uid,:expiry,false)'),{'token':digest(token),'uid':uid,'expiry':int(time.time())+600})
    attacker=TestClient(app,base_url=ORIGIN,client=('127.0.0.2',50001))
    attack_headers=headers(attacker)
    codes=[attacker.post('/api/auth/reset-password',headers=attack_headers,json={'token':'x'*43,'password':PASSWORD}).status_code for _ in range(8)]
    assert codes==[400]*8,codes
    result=victim.post('/api/auth/reset-password',headers=headers(victim),json={'token':token,'password':PASSWORD})
    assert result.status_code==429,result.text
    # A valid victim token is still unused; no actual credential was changed.
    with app.state.engine.connect() as db:
        assert db.execute(text('SELECT used FROM password_resets WHERE token_hash=:token'),{'token':digest(token)}).scalar_one() is False
    print('CONFIRMED: eight invalid resets from another loopback IP block a valid victim reset, HTTP 429')

def test_webhook_ack_waits_for_slow_provider():
    c,aid=buyer();o=order(c,aid);oid=start(c,o);gateway.pay(oid)
    original=gateway._request
    def delayed(method,path,payload=None,headers=None):
        if method=='GET' and path=='orders/'+oid:time.sleep(5.2)
        return original(method,path,payload,headers)
    gateway._request=delayed
    try:
        begun=time.monotonic();response=event(c,oid);elapsed=time.monotonic()-begun
    finally:gateway._request=original
    assert response.status_code==200,response.text
    assert elapsed>=5.2,elapsed
    print('CONFIRMED: synthetic slow provider delays webhook acknowledgment %.2f seconds'%elapsed)

def test_basic_access_and_csrf_controls():
    c,aid=buyer();o=order(c,aid)
    other,_=buyer()
    assert other.get('/api/orders/'+str(o['id'])).status_code==404
    assert other.get('/api/admin/orders').status_code==403
    assert other.post('/api/orders/'+str(o['id'])+'/cancel',headers=headers(other)).status_code==404
    assert c.post('/api/orders/'+str(o['id'])+'/cancel').status_code==403
    assert post(c,endpoint(o,'checkout')).status_code==200
    raw=b'{}'
    assert c.post('/api/razorpay/webhook',content=raw,headers={'x-razorpay-event-id':'synthetic-invalid','x-razorpay-signature':'0'*64}).status_code==400
    print('PROTECTION: order ownership, admin restriction, CSRF and invalid webhook signature rejected')
'''
runner=TestRunner(stage)
runner.executor.docker=r'C:\Users\HET\AppData\Local\Programs\DockerDesktop\resources\bin\docker.exe'
runner.executor.image='projectforge-relational-runtime:local'
(stage/'.projectforge').mkdir(exist_ok=True)
(stage/'.projectforge/capture_payment_screenshots').touch() # Existing runner's switch for pytest stdout.
result=runner._payment_gate('security_audit',prefix+tests)
(DEST/'synthetic-results.json').write_text(json.dumps(result.model_dump(),indent=2),encoding='utf-8')
print(json.dumps(result.model_dump(),indent=2))
