import json,secrets,threading,subprocess,time
import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from app.main import app
ORIGIN=json.loads(open('backend/app/identity.json',encoding='utf-8').read())['public_origin']
PASSWORD=secrets.token_urlsafe(24)
@pytest.fixture(scope='module',autouse=True)
def application_lifespan():
    with TestClient(app,base_url=ORIGIN,client=('127.0.0.1',49999)):
        assert app.state.engine.dialect.name=='postgresql'
        with app.state.engine.connect() as db:
            revisions=sorted(db.execute(text('SELECT revision FROM projectforge_migrations')).scalars().all())
        expected=['0001','0002','0003','0004'] if getattr(app.state,'payment_simulator',False) else ['0001','0002','0003']
        if getattr(app.state,'razorpay_test',False):expected=['0001','0002','0003','0004_razorpay_test']
        if hasattr(app.state,'fulfillment_view'):expected.append('0005_delivery')
        assert revisions==expected,revisions
        yield
def headers(c):return {'Origin':ORIGIN,'X-CSRF-Token':c.get('/api/auth/csrf').json()['csrf_token']}
def customer(email):
    c=TestClient(app,base_url=ORIGIN,client=('127.0.0.1',50000))
    payload={'email':email,'password':PASSWORD,'name':'Synthetic buyer'}
    assert c.post('/api/auth/register',headers=headers(c),json=payload).status_code==200
    assert c.post('/api/auth/login',headers=headers(c),json={'email':email,'password':PASSWORD}).status_code==200
    address={'label':'Test','full_name':'Synthetic buyer','line1':'1 Test road','line2':'','city':'Test city','region':'Test region','postal_code':'00001','country':'IN'}
    made=c.post('/api/account/addresses',headers=headers(c),json=address);assert made.status_code==201
    return c,made.json()['id']
def add(c,sku,quantity=1):
    quote=c.get('/api/cart').json()
    return c.put('/api/cart/items/'+sku,headers=headers(c),json={'quantity':quantity,'expected_version':quote['version']})
def request(c,aid,key=None):
    q=c.get('/api/cart').json()
    return {'address_id':aid,'cart_version':q['version'],'quote_hash':q['quote_hash'],'idempotency_key':key or secrets.token_urlsafe(24)}
def stock(sku):
    with app.state.engine.connect() as db:return db.execute(text('SELECT stock_quantity FROM variants WHERE sku=:sku'),{'sku':sku}).scalar_one()

from app.identity_runtime import create_admin

def post(c,path,body):return c.post(path,headers=headers(c),json=body)
def key():return {'idempotency_key':secrets.token_urlsafe(24)}
def order(c,aid):
    assert add(c,'PACK-OLIVE-18').status_code==200
    result=post(c,'/api/orders',request(c,aid));assert result.status_code==201,result.text
    return result.json()
def start(c,o):
    result=post(c,f"/api/simulation/orders/{o['id']}/payment",key());assert result.status_code==200,result.text
    p=result.json();assert p['mode']=='offline_simulator' and p['real_money_collected'] is False
    assert p['amount_minor']==o['total_minor'] and p['currency']==o['currency']
    return p
def outcome(p,value='succeeded'):return {**key(),'outcome':value,'amount_minor':p['amount_minor'],'currency':p['currency']}
def buyer():return customer('sim-'+secrets.token_hex(7)+'@example.com')
def operator():
    email='admin-'+secrets.token_hex(7)+'@example.com'
    create_admin(app.state.engine,app.state.identity_metadata,email,PASSWORD)
    c=TestClient(app,base_url=ORIGIN,client=('127.0.0.1',50000))
    assert post(c,'/api/auth/login',{'email':email,'password':PASSWORD}).status_code==200
    return c

def test_pending_success_amount_authority_duplicate_and_late_outcome():
    c,aid=buyer();before=stock('PACK-OLIVE-18');o=order(c,aid)
    begin=key();url=f"/api/simulation/orders/{o['id']}/payment"
    p=post(c,url,begin).json();assert p['state']=='pending'
    assert post(c,url,begin).json()['id']==p['id']
    assert post(c,url,key()).json()['id']==p['id']
    url=f"/api/simulation/payments/{p['id']}/resolve";body=outcome(p)
    assert post(c,url,{**body,'amount_minor':1}).status_code==409
    assert post(c,url,{**body,'currency':'USD'}).status_code==409
    assert post(c,url,{**body,'card_number':'not-accepted'}).status_code==422
    assert c.post(url,json=body).status_code==403
    assert c.post(url,headers={'Origin':'https://hostile.invalid'},json=body).status_code==403
    assert post(c,url,body).json()['state']=='succeeded'
    assert post(c,url,body).json()['state']=='succeeded'
    assert post(c,url,{**body,'outcome':'failed'}).status_code==409
    assert post(c,url,outcome(p,'cancelled')).status_code==409
    assert stock('PACK-OLIVE-18')==before-1
    with app.state.engine.begin() as db:db.execute(text('UPDATE orders SET expires_at=0 WHERE id=:id'),{'id':o['id']})
    app.state.expire_reservations()
    saved=c.get('/api/orders/'+str(o['id'])).json()
    assert saved['state']=='simulated_paid' and saved['payment_status']=='succeeded'
    assert post(c,f"/api/orders/{o['id']}/cancel",{}).status_code==409
    assert stock('PACK-OLIVE-18')==before-1

@pytest.mark.parametrize('terminal',['failed','cancelled','expired','order_cancel'])
def test_failure_cancel_and_expiry_release_once(terminal):
    c,aid=buyer();before=stock('PACK-OLIVE-18');o=order(c,aid);p=start(c,o)
    url=f"/api/simulation/payments/{p['id']}/resolve"
    if terminal=='expired':
        with app.state.engine.begin() as db:db.execute(text('UPDATE orders SET expires_at=0 WHERE id=:id'),{'id':o['id']})
        assert post(c,url,outcome(p)).status_code==409
        assert c.get('/api/orders/'+str(o['id'])).json()['payment_status']=='expired'
    elif terminal=='order_cancel':
        assert post(c,f"/api/orders/{o['id']}/cancel",{}).status_code==200
        assert c.get('/api/orders/'+str(o['id'])).json()['payment_status']=='cancelled'
    else:
        body=outcome(p,terminal)
        assert post(c,url,body).json()['state']==terminal
        assert post(c,url,body).json()['state']==terminal
    assert post(c,url,outcome(p)).status_code==409
    app.state.expire_reservations();app.state.expire_reservations()
    assert stock('PACK-OLIVE-18')==before
    # Refund permission and session authority were checked server-side above.
    assert post(c,f"/api/simulation/orders/{o['id']}/payment",key()).status_code==409

def test_ownership_and_admin_refund_failed_retry_success_release_once():
    c,aid=buyer();other,_=buyer();admin=operator();before=stock('PACK-OLIVE-18')
    o=order(c,aid);p=start(c,o);url=f"/api/simulation/payments/{p['id']}/resolve"
    assert post(other,f"/api/simulation/orders/{o['id']}/payment",key()).status_code==404
    assert post(other,url,outcome(p)).status_code==404
    refund_url=f"/api/admin/simulation/payments/{p['id']}/refund"
    assert post(c,refund_url,key()).status_code==403
    assert post(admin,refund_url,key()).status_code==409
    assert post(c,url,outcome(p)).status_code==200
    first=key();r=post(admin,refund_url,first).json();assert r['state']=='pending' and r['amount_minor']==p['amount_minor']
    assert post(admin,refund_url,first).json()['id']==r['id']
    assert post(admin,refund_url,key()).status_code==409
    resolve=f"/api/admin/simulation/refunds/{r['id']}/resolve"
    assert post(c,resolve,{**key(),'outcome':'succeeded'}).status_code==403
    failed={**key(),'outcome':'failed'}
    assert post(admin,resolve,failed).json()['state']=='failed'
    assert post(admin,resolve,failed).json()['state']=='failed'
    assert stock('PACK-OLIVE-18')==before-1
    r=post(admin,refund_url,key()).json();assert r['state']=='pending'
    resolve=f"/api/admin/simulation/refunds/{r['id']}/resolve";body={**key(),'outcome':'succeeded'}
    assert post(admin,resolve,body).json()['state']=='succeeded'
    assert post(admin,resolve,body).json()['state']=='succeeded'
    assert post(admin,resolve,{**key(),'outcome':'failed'}).status_code==409
    assert post(admin,refund_url,key()).status_code==409
    assert stock('PACK-OLIVE-18')==before
    saved=c.get('/api/orders/'+str(o['id'])).json()
    assert saved['state']=='simulated_refunded' and saved['payment_status']=='refunded'
    with app.state.engine.connect() as db:
        assert db.execute(text("SELECT count(*) FROM simulated_refunds WHERE payment_id=:id AND state='succeeded'"),{'id':p['id']}).scalar_one()==1
        assert db.execute(text("SELECT count(*) FROM audit_records WHERE action LIKE 'simulation_%'")).scalar_one()>0

def test_concurrent_opposite_outcomes_only_one_wins():
    c,aid=buyer();o=order(c,aid);p=start(c,o);before=stock('PACK-OLIVE-18')
    cookies=dict(c.cookies);barrier=threading.Barrier(2);results=[]
    def submit(value):
        client=TestClient(app,base_url=ORIGIN,client=('127.0.0.1',50000));client.cookies.update(cookies)
        h=headers(client);barrier.wait()
        results.append(client.post(f"/api/simulation/payments/{p['id']}/resolve",headers=h,json=outcome(p,value)).status_code)
    workers=[threading.Thread(target=submit,args=(v,)) for v in ('succeeded','cancelled')]
    [w.start() for w in workers];[w.join(25) for w in workers]
    assert all(not w.is_alive() for w in workers) and sorted(results)==[200,409],results
    saved=c.get('/api/orders/'+str(o['id'])).json()
    assert stock('PACK-OLIVE-18')==before+(1 if saved['state']=='cancelled' else 0)

def test_payment_state_and_event_replay_survive_process_restart():
    c,aid=buyer();o=order(c,aid);p=start(c,o);body=outcome(p);url=f"/api/simulation/payments/{p['id']}/resolve"
    assert post(c,url,body).status_code==200
    cookies=dict(c.cookies);before=stock('PACK-OLIVE-18')
    for _ in range(2):
        server=subprocess.Popen(['python','-m','uvicorn','app.main:app','--host','127.0.0.1','--port','8012'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        try:
            for i in range(100):
                try:
                    response=httpx.get('http://127.0.0.1:8012/api/store',timeout=1)
                    if response.status_code==200:break
                except httpx.HTTPError:pass
                time.sleep(.1)
            else:raise AssertionError('Restarted simulator failed to start')
            with httpx.Client(base_url='http://127.0.0.1:8012',cookies=cookies) as remote:
                saved=remote.get('/api/orders/'+str(o['id']));assert saved.status_code==200,saved.text
                assert saved.json()['state']=='simulated_paid'
                csrf=remote.get('/api/auth/csrf').json()['csrf_token']
                replay=remote.post(url,json=body,headers={'Origin':ORIGIN,'X-CSRF-Token':csrf})
                assert replay.status_code==200 and replay.json()['state']=='succeeded',replay.text
        finally:server.terminate();server.wait(timeout=5)
    assert stock('PACK-OLIVE-18')==before

def test_simulator_rate_limit_is_persistent_and_has_no_duplicate_effects():
    c,aid=buyer();o=order(c,aid);cookies=dict(c.cookies)
    limited=TestClient(app,base_url=ORIGIN,client=('127.0.0.9',50000));limited.cookies.update(cookies)
    body=key();url=f"/api/simulation/orders/{o['id']}/payment"
    for _ in range(30):assert post(limited,url,body).status_code==200
    denied=post(limited,url,body)
    assert denied.status_code==429 and 'Retry-After' in denied.headers
    another=TestClient(app,base_url=ORIGIN,client=('127.0.0.10',50000));another.cookies.update(cookies)
    assert post(another,url,body).status_code==429
    with app.state.engine.connect() as db:
        assert db.execute(text('SELECT count(*) FROM simulated_payments WHERE order_id=:id'),{'id':o['id']}).scalar_one()==1

def test_upgrade_preserves_phase5_orders_and_rejects_downgrade():
    from app.order_runtime import create_app as legacy_app
    from app.payment_runtime import create_app as simulator_app
    from sqlalchemy import create_engine
    dbname='upgrade_'+secrets.token_hex(5)
    with app.state.engine.connect().execution_options(isolation_level='AUTOCOMMIT') as conn:
        conn.execute(text('CREATE DATABASE '+dbname+' TEMPLATE template0 ENCODING '+"'UTF8'"))
    url=app.state.engine.url.set(database=dbname).render_as_string(hide_password=False)
    previous=legacy_app(database_url=url)
    with TestClient(previous,base_url=ORIGIN,client=('127.0.0.1',50000)) as c:
        email='upgrade@example.com'
        assert post(c,'/api/auth/register',{'email':email,'name':'Upgrade buyer','password':PASSWORD}).status_code==200
        assert post(c,'/api/auth/login',{'email':email,'password':PASSWORD}).status_code==200
        address={'label':'Test','full_name':'Buyer','line1':'1 Test road','line2':'','city':'Test','region':'Test','postal_code':'00001','country':'IN'}
        aid=post(c,'/api/account/addresses',address).json()['id']
        o=order(c,aid);cookies=dict(c.cookies)
        assert o['payment_status']=='not_implemented'
        with previous.state.engine.connect() as db:assert db.execute(text('SELECT count(*) FROM projectforge_migrations')).scalar_one()==3
    upgraded=simulator_app(database_url=url)
    with TestClient(upgraded,base_url=ORIGIN,client=('127.0.0.1',50000)) as c:
        c.cookies.update(cookies)
        saved=c.get('/api/orders/'+str(o['id'])).json()
        assert saved['items']==o['items'] and saved['total_minor']==o['total_minor'] and saved['address_snapshot']==o['address_snapshot']
        p=start(c,saved)
        assert post(c,f"/api/simulation/payments/{p['id']}/resolve",outcome(p)).json()['state']=='succeeded'
        with upgraded.state.engine.connect() as db:
            assert sorted(db.execute(text('SELECT revision FROM projectforge_migrations')).scalars())==['0001','0002','0003','0004','0005_delivery']
    # Old code must not operate against a schema it cannot interpret.
    with pytest.raises(Exception):
        with TestClient(legacy_app(database_url=url)):pass


def delivery(c,oid,expected,target):
    return post(c,f'/api/admin/orders/{oid}/fulfillment',{'expected_status':expected,'status':target})

def paid_order():
    c,aid=buyer();o=order(c,aid);p=start(c,o)
    assert post(c,f"/api/simulation/payments/{p['id']}/resolve",outcome(p)).status_code==200
    return c,o,p

def test_delivery_authority_transitions_replay_and_stock():
    c,o,p=paid_order();a=operator();oid=o['id'];before=stock('PACK-OLIVE-18')
    url=f'/api/admin/orders/{oid}/fulfillment'
    body={'expected_status':'not_packed','status':'packed'}
    assert delivery(c,oid,'not_packed','packed').status_code==403
    assert a.post(url,json=body).status_code==403
    assert a.post(url,headers={**headers(a),'Origin':'https://hostile.invalid'},json=body).status_code==403
    assert post(a,url,{**body,'status':'invalid'}).status_code==422
    assert post(a,url,{**body,'role':'admin'}).status_code==422
    assert delivery(a,oid,'not_packed','delivered').status_code==409
    assert delivery(a,oid,'not_packed','packed').json()['status']=='packed'
    assert delivery(a,oid,'not_packed','packed').json()['status']=='packed'
    assert delivery(a,oid,'packed','shipped').json()['status']=='shipped'
    assert delivery(a,oid,'not_packed','packed').status_code==409
    assert delivery(a,oid,'shipped','delivered').json()['status']=='delivered'
    assert delivery(a,oid,'shipped','delivered').status_code==200
    saved=c.get(f'/api/orders/{oid}').json()
    assert saved['state']=='simulated_paid' and saved['fulfillment']['status']=='delivered'
    assert saved['fulfillment']['next_status'] is None
    assert stock('PACK-OLIVE-18')==before
    assert post(a,f"/api/admin/simulation/payments/{p['id']}/refund",key()).status_code==409
    with app.state.engine.connect() as db:
        assert db.execute(text("SELECT count(*) FROM audit_records WHERE resource_id=:oid AND action LIKE 'delivery_%'"),{'oid':str(oid)}).scalar_one()==3
    other,_=buyer();assert other.get(f'/api/orders/{oid}').status_code==404
    # A new application instance reuses the migration and persisted delivery state.
    from app.payment_runtime import create_app
    fresh=create_app()
    with TestClient(fresh,base_url=ORIGIN,client=('127.0.0.1',50000)) as restarted:
        restarted.cookies.update(dict(c.cookies))
        assert restarted.get(f'/api/orders/{oid}').json()['fulfillment']['status']=='delivered'

def test_delivery_blocks_unpaid_cancelled_and_pending_refund():
    c,aid=buyer();o=order(c,aid);a=operator()
    assert delivery(a,o['id'],'not_packed','packed').status_code==409
    assert post(c,f"/api/orders/{o['id']}/cancel",{}).status_code==200
    assert delivery(a,o['id'],'not_packed','packed').status_code==409
    c,o,p=paid_order()
    r=post(a,f"/api/admin/simulation/payments/{p['id']}/refund",key())
    assert r.status_code==200
    assert delivery(a,o['id'],'not_packed','packed').status_code==409
    assert post(a,f"/api/admin/simulation/refunds/{r.json()['id']}/resolve",{**key(),'outcome':'succeeded'}).status_code==200
    assert delivery(a,o['id'],'not_packed','packed').status_code==409

def test_delivery_concurrent_repeat_has_one_audit_event():
    c,o,p=paid_order();a=operator();barrier=threading.Barrier(2);results=[]
    def advance():
        client=TestClient(app,base_url=ORIGIN,client=('127.0.0.1',50000));client.cookies.update(dict(a.cookies))
        h=headers(client);barrier.wait()
        results.append(client.post(f"/api/admin/orders/{o['id']}/fulfillment",headers=h,json={'expected_status':'not_packed','status':'packed'}).status_code)
    workers=[threading.Thread(target=advance) for _ in range(2)]
    for worker in workers:worker.start()
    for worker in workers:worker.join()
    assert results==[200,200]
    with app.state.engine.connect() as db:
        assert db.execute(text("SELECT count(*) FROM audit_records WHERE resource_id=:oid AND action='delivery_packed'"),{'oid':str(o['id'])}).scalar_one()==1
