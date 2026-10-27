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
        if getattr(app.state,'shipping_details_version',0):expected.append('0006_tracking')
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
            assert sorted(db.execute(text('SELECT revision FROM projectforge_migrations')).scalars())==['0001','0002','0003','0004','0005_delivery','0006_tracking']
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


def shipping(c,oid,version=0,courier='Example Courier',number='DEMO-TRACK-001'):
    return post(c,f'/api/admin/orders/{oid}/shipping-details',{'expected_version':version,'courier_name':courier,'tracking_number':number})

def test_tracking_authorization_validation_and_no_side_effects():
    c,o,p=paid_order();a=operator();oid=o['id'];url=f'/api/admin/orders/{oid}/shipping-details'
    body={'expected_version':0,'courier_name':'Example Courier','tracking_number':'DEMO-001'}
    assert shipping(c,oid).status_code==403
    anon=TestClient(app,base_url=ORIGIN,client=('127.0.0.1',50000))
    assert post(anon,url,body).status_code in (401,403)
    assert a.post(url,json=body).status_code==403
    assert a.post(url,headers={**headers(a),'Origin':'https://hostile.invalid'},json=body).status_code==403
    for patch in ({'courier_name':''},{'courier_name':'   '},{'tracking_number':' '},
                  {'courier_name':'X'*101},{'tracking_number':'1'*101},
                  {'courier_name':'bad\nname'},{'tracking_number':'bad\tvalue'},
                  {'courier_name':'\u202eCourier'},{'tracking_number':'<script>alert(1)</script>'},
                  {'courier_name':'<img src=x onerror=alert(1)>'},
                  {'expected_version':-1},{'expected_version':True},{'expected_version':'0'},
                  {'updated_by':1},{'tracking_url':'https://hostile.invalid'}):
        result=post(a,url,{**body,**patch});assert result.status_code==422,(patch,result.text)
    assert post(a,url,{'expected_version':0,'courier_name':'Courier'}).status_code==422
    assert shipping(a,999999999).status_code==404
    with app.state.engine.connect() as db:
        assert db.execute(text('SELECT count(*) FROM order_shipping_details WHERE order_id=:id'),{'id':oid}).scalar_one()==0

def test_tracking_save_edit_replay_conflict_customer_and_restart():
    c,o,p=paid_order();a=operator();oid=o['id'];before=c.get(f'/api/orders/{oid}').json();quantity=stock('PACK-OLIVE-18')
    first=shipping(a,oid,courier='  Example Courier  ',number='  DEMO-001  ')
    assert first.status_code==200,first.text
    details=first.json()['shipping_details'];assert details['courier_name']=='Example Courier' and details['tracking_number']=='DEMO-001' and details['version']==1
    assert first.json()['status']=='not_packed'
    assert shipping(a,oid,number='DEMO-001').json()['shipping_details']==details
    assert shipping(a,oid,number='STALE').status_code==409
    second=shipping(a,oid,1,courier='India Post',number='DEMO-002-IN')
    assert second.status_code==200 and second.json()['shipping_details']['version']==2
    saved=c.get(f'/api/orders/{oid}').json()
    assert saved['fulfillment']['shipping_details']['tracking_number']=='DEMO-002-IN'
    assert 'updated_by' not in saved['fulfillment']['shipping_details']
    for field in ('state','total_minor','currency','items','address_snapshot','payment_status'):
        assert saved[field]==before[field]
    assert stock('PACK-OLIVE-18')==quantity
    other,_=buyer();assert other.get(f'/api/orders/{oid}').status_code==404
    assert other.get('/api/admin/orders').status_code==403
    assert shipping(a,oid,0,number='DEMO-001').status_code==409
    with app.state.engine.connect() as db:
        assert db.execute(text("SELECT count(*) FROM audit_records WHERE resource_id=:id AND action='shipping_details_updated'"),{'id':str(oid)}).scalar_one()==2
    from app.payment_runtime import create_app
    fresh=create_app()
    with TestClient(fresh,base_url=ORIGIN,client=('127.0.0.1',50000)) as restarted:
        restarted.cookies.update(dict(c.cookies))
        assert restarted.get(f'/api/orders/{oid}').json()['fulfillment']['shipping_details']==saved['fulfillment']['shipping_details']

def test_tracking_competing_edits_do_not_overwrite():
    c,o,p=paid_order();a=operator();barrier=threading.Barrier(2);results=[]
    assert shipping(a,o['id']).status_code==200
    def edit(number):
        client=TestClient(app,base_url=ORIGIN,client=('127.0.0.1',50000));client.cookies.update(dict(a.cookies))
        h=headers(client);barrier.wait()
        response=client.post(f"/api/admin/orders/{o['id']}/shipping-details",headers=h,json={'expected_version':1,'courier_name':'Example Courier','tracking_number':number})
        results.append((number,response.status_code))
    workers=[threading.Thread(target=edit,args=(number,)) for number in ('EDIT-A','EDIT-B')]
    for worker in workers:worker.start()
    for worker in workers:worker.join()
    assert sorted(code for _,code in results)==[200,409]
    winner=next(number for number,code in results if code==200)
    saved=c.get(f"/api/orders/{o['id']}").json()['fulfillment']['shipping_details']
    assert saved['tracking_number']==winner and saved['version']==2

def test_tracking_state_rules_and_delivery_do_not_require_a_courier():
    a=operator();c,aid=buyer();unpaid=order(c,aid)
    assert shipping(a,unpaid['id']).status_code==409
    assert post(c,f"/api/orders/{unpaid['id']}/cancel",{}).status_code==200
    assert shipping(a,unpaid['id']).status_code==409
    c,o,p=paid_order();assert shipping(a,o['id']).status_code==200
    assert delivery(a,o['id'],'not_packed','packed').status_code==200
    assert shipping(a,o['id'],1,number='CORRECTED').status_code==200
    assert delivery(a,o['id'],'packed','shipped').status_code==200
    assert shipping(a,o['id'],2,number='FINAL').status_code==200
    assert delivery(a,o['id'],'shipped','delivered').status_code==200
    assert shipping(a,o['id'],3,number='AFTER-DELIVERY').status_code==409
    saved=c.get(f"/api/orders/{o['id']}").json()['fulfillment']
    assert saved['shipping_details']['tracking_number']=='FINAL' and not saved['can_edit_shipping']
    c,o,p=paid_order()
    refund=post(a,f"/api/admin/simulation/payments/{p['id']}/refund",key())
    assert refund.status_code==200
    assert shipping(a,o['id']).status_code==409
    assert post(a,f"/api/admin/simulation/refunds/{refund.json()['id']}/resolve",{**key(),'outcome':'succeeded'}).status_code==200
    assert shipping(a,o['id']).status_code==409
    # Retain the existing manual workflow for old orders without tracking data.
    c,o,p=paid_order()
    for previous,target in [('not_packed','packed'),('packed','shipped'),('shipped','delivered')]:
        assert delivery(a,o['id'],previous,target).status_code==200
    assert c.get(f"/api/orders/{o['id']}").json()['fulfillment']['shipping_details'] is None

def test_tracking_migration_preserves_existing_delivery_fixture():
    from app.payment_runtime import create_app
    dbname='tracking_upgrade_'+secrets.token_hex(5)
    with app.state.engine.connect().execution_options(isolation_level='AUTOCOMMIT') as db:
        db.execute(text('CREATE DATABASE '+dbname+' TEMPLATE template0 ENCODING '+"'UTF8'"))
    url=app.state.engine.url.set(database=dbname).render_as_string(hide_password=False)
    fixture=create_app(database_url=url)
    with TestClient(fixture,base_url=ORIGIN,client=('127.0.0.1',50000)) as c:
        assert post(c,'/api/auth/register',{'email':'tracking-upgrade@example.com','name':'Upgrade buyer','password':PASSWORD}).status_code==200
        assert post(c,'/api/auth/login',{'email':'tracking-upgrade@example.com','password':PASSWORD}).status_code==200
        address={'label':'Test','full_name':'Buyer','line1':'1 Test road','line2':'','city':'Test','region':'Test','postal_code':'00001','country':'IN'}
        aid=post(c,'/api/account/addresses',address).json()['id']
        existing=order(c,aid);payment=start(c,existing)
        assert post(c,f"/api/simulation/payments/{payment['id']}/resolve",outcome(payment)).status_code==200
        from app.identity_runtime import create_admin
        create_admin(fixture.state.engine,fixture.state.identity_metadata,'tracking-admin@example.com',PASSWORD)
        admin=TestClient(fixture,base_url=ORIGIN,client=('127.0.0.1',50000))
        assert post(admin,'/api/auth/login',{'email':'tracking-admin@example.com','password':PASSWORD}).status_code==200
        assert delivery(admin,existing['id'],'not_packed','packed').status_code==200
        cookies=dict(c.cookies)
        with fixture.state.engine.begin() as db:
            # Recreate the pre-tracking database shape without touching any old table.
            db.execute(text('DROP TABLE order_shipping_details'))
            db.execute(text("DELETE FROM projectforge_migrations WHERE revision='0006_tracking'"))
            prior=dict(db.execute(text('SELECT revision,checksum FROM projectforge_migrations')).all())
            products=db.execute(text('SELECT count(*) FROM products')).scalar_one()
    upgraded=create_app(database_url=url)
    with TestClient(upgraded,base_url=ORIGIN,client=('127.0.0.1',50000)) as c:
        c.cookies.update(cookies)
        saved=c.get(f"/api/orders/{existing['id']}").json()
        assert saved['items']==existing['items'] and saved['total_minor']==existing['total_minor']
        assert saved['fulfillment']['status']=='packed' and saved['fulfillment']['shipping_details'] is None
        assert saved['payment_status']=='succeeded'
        with upgraded.state.engine.connect() as db:
            after=dict(db.execute(text('SELECT revision,checksum FROM projectforge_migrations')).all())
            assert all(after[revision]==value for revision,value in prior.items())
            assert set(after)==set(prior)|{'0006_tracking'}
            assert db.execute(text('SELECT count(*) FROM products')).scalar_one()==products
            assert db.execute(text('SELECT count(*) FROM order_shipping_details')).scalar_one()==0


def shipment_paid_order():
    c,aid=buyer();o=order(c,aid);payment=start(c,o)
    if getattr(app.state,'payment_simulator',False):
        assert post(c,f"/api/simulation/payments/{payment['id']}/resolve",outcome(payment)).status_code==200
    else:
        pid=gateway.pay(payment)
        assert post(c,endpoint(o,'verify'),callback(payment,pid)).status_code==200
    return c,o

def test_customer_shipment_ownership_projection_history_and_restart():
    c,o=shipment_paid_order();a=operator();url=f"/api/orders/{o['id']}/shipment"
    anon=TestClient(app,base_url=ORIGIN,client=('127.0.0.1',50000))
    assert anon.get(url).status_code==401
    stranger,_=buyer();assert stranger.get(url).status_code==404
    assert a.get(url).status_code==404  # admin role does not confer customer ownership
    assert c.get('/api/orders/2147483647/shipment').status_code==404
    for value in ('0','-1','2147483648','bad'):
        assert c.get('/api/orders/'+value+'/shipment').status_code==422
    response=c.get(url);assert response.status_code==200
    assert 'no-store' in response.headers.get('cache-control','')
    original=response.json()
    assert original['availability']=='active' and original['status']=='not_packed'
    assert original['history']==[{'status':'placed','recorded_at':o['created_at']}]
    assert original['shipping_details'] is None and original['estimated_delivery'] is None
    assert original['update_source']=='store_manual'
    assert set(original)=={'order_id','availability','status','updated_at','shipping_details','history','update_source','estimated_delivery'}
    assert post(a,f"/api/admin/orders/{o['id']}/shipping-details",{'expected_version':0,'courier_name':'Example Courier','tracking_number':'DEMO-SHIP-001'}).status_code==200
    before=stock('PACK-OLIVE-18')
    for previous,target in [('not_packed','packed'),('packed','shipped'),('shipped','delivered')]:
        body={'expected_status':previous,'status':target}
        path=f"/api/admin/orders/{o['id']}/fulfillment"
        assert post(a,path,body).status_code==200
        assert post(a,path,body).status_code==200
        data=c.get(url).json();assert data['status']==target
        assert [item['status'] for item in data['history']]==['placed','packed','shipped','delivered'][:len(data['history'])]
    data=c.get(url).json()
    assert data['availability']=='delivered' and len(data['history'])==4
    assert data['shipping_details']['tracking_number']=='DEMO-SHIP-001'
    assert stock('PACK-OLIVE-18')==before
    with app.state.engine.connect() as db:
        times=db.execute(text("SELECT created_at FROM audit_records WHERE resource='order' AND resource_id=:id AND action IN ('delivery_packed','delivery_shipped','delivery_delivered') ORDER BY id"),{'id':str(o['id'])}).scalars().all()
        assert [event['recorded_at'] for event in data['history'][1:]]==times
    if getattr(app.state,'payment_simulator',False):from app.payment_runtime import create_app
    else:from app.razorpay_runtime import create_app
    fresh=create_app()
    with TestClient(fresh,base_url=ORIGIN,client=('127.0.0.1',50000)) as restarted:
        restarted.cookies.update(dict(c.cookies))
        assert restarted.get(url).json()==data

def test_customer_shipment_unpaid_cancelled_and_expired():
    c,aid=buyer();o=order(c,aid);url=f"/api/orders/{o['id']}/shipment"
    assert c.get(url).json()['availability']=='awaiting_payment'
    assert post(c,f"/api/orders/{o['id']}/cancel",{}).status_code==200
    result=c.get(url).json();assert result['availability']=='cancelled'
    assert [e['status'] for e in result['history']]==['placed']
    c,aid=buyer();o=order(c,aid)
    with app.state.engine.begin() as db:
        db.execute(text('UPDATE orders SET expires_at=:time WHERE id=:id'),{'time':int(time.time())-1,'id':o['id']})
    expired=c.get(f"/api/orders/{o['id']}/shipment").json()
    assert expired['availability']=='expired' and expired['shipping_details'] is None

def test_customer_shipment_legacy_missing_milestones_are_not_invented():
    c,o=shipment_paid_order();a=operator()
    assert post(a,f"/api/admin/orders/{o['id']}/fulfillment",{'expected_status':'not_packed','status':'packed'}).status_code==200
    # Model a legacy record whose status exists but historical audit detail is absent.
    with app.state.engine.begin() as db:
        db.execute(text("DELETE FROM audit_records WHERE resource='order' AND resource_id=:id AND action='delivery_packed'"),{'id':str(o['id'])})
    result=c.get(f"/api/orders/{o['id']}/shipment").json()
    assert result['status']=='packed'
    assert result['history']==[{'status':'placed','recorded_at':o['created_at']}]
    assert result['estimated_delivery'] is None


def test_customer_shipment_refund_hold_and_refunded_state():
    c,o,p=paid_order();a=operator();url=f"/api/orders/{o['id']}/shipment"
    refund=post(a,f"/api/admin/simulation/payments/{p['id']}/refund",key())
    assert refund.status_code==200
    assert c.get(url).json()['availability']=='on_hold'
    assert post(a,f"/api/admin/simulation/refunds/{refund.json()['id']}/resolve",{**key(),'outcome':'succeeded'}).status_code==200
    result=c.get(url).json()
    assert result['availability']=='refunded' and result['status']=='not_packed'
    assert [event['status'] for event in result['history']]==['placed']
