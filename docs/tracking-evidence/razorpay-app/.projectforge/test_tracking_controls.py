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
        if hasattr(app.state,'fulfillment_view'):expected.extend(['0005_delivery','0006_tracking'])
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
import copy,hashlib,hmac
from app.razorpay_client import RazorpayTestClient,ProviderUnavailable
SECRET='synthetic-checkout-secret'
WEBHOOK='synthetic-webhook-secret-for-tests'
class FakeProvider(RazorpayTestClient):
    def __init__(self):
        super().__init__('rzp_test_SYNTHETIC',SECRET,WEBHOOK,'acc_SYNTHETIC')
        self.orders={};self.pays={};self.refunds={};self.refund_keys={};self.creates=0;self.lost_create=False;self.lost_refund=False;self.refund_calls=[]
    def _request(self,method,path,payload=None,headers=None):
        if method=='POST' and path=='orders':
            self.creates+=1;oid='order_'+str(self.creates)
            value={'id':oid,'entity':'order','status':'created',**payload};self.orders[oid]=value
            if self.lost_create:self.lost_create=False;raise ProviderUnavailable('synthetic lost response')
            return copy.deepcopy(value)
        if path.startswith('orders?'):
            from urllib.parse import parse_qs
            receipt=parse_qs(path.split('?')[1])['receipt'][0]
            return {'items':[copy.deepcopy(v) for v in self.orders.values() if v['receipt']==receipt]}
        if method=='GET' and path.startswith('orders/'):
            oid=path.split('/')[1]
            if path.endswith('/payments'):return {'items':[copy.deepcopy(v) for v in self.pays.values() if v['order_id']==oid]}
            return copy.deepcopy(self.orders[oid])
        if method=='GET' and path.startswith('payments/'):return copy.deepcopy(self.pays[path.split('/')[1]])
        if method=='POST' and path.endswith('/refund'):
            pid=path.split('/')[1];key=headers['X-Refund-Idempotency'];self.refund_calls.append((key,copy.deepcopy(payload)))
            if key not in self.refund_keys:
                rid='rfnd_'+str(len(self.refunds)+1);self.refund_keys[key]=rid
                self.refunds[rid]={'entity':'refund','id':rid,'payment_id':pid,'amount':payload['amount'],'currency':'INR','status':'pending'}
            value=self.refunds[self.refund_keys[key]]
            if self.lost_refund:self.lost_refund=False;raise ProviderUnavailable('synthetic lost refund response')
            return copy.deepcopy(value)
        if method=='GET' and path.startswith('refunds/'):return copy.deepcopy(self.refunds[path.split('/')[1]])
        raise AssertionError((method,path))
    def pay(self,oid,status='captured'):
        pid='pay_'+str(len(self.pays)+1);o=self.orders[oid]
        self.pays[pid]={'entity':'payment','id':pid,'order_id':oid,'amount':o['amount'],'currency':o['currency'],'status':status,'captured':status=='captured','amount_refunded':0}
        if status=='captured':o['status']='paid'
        return pid
def sign(raw,secret=SECRET):return hmac.new(secret.encode(),raw,hashlib.sha256).hexdigest()

from app.identity_runtime import create_admin
from app.razorpay_client import ProviderMismatch
gateway=FakeProvider()
@pytest.fixture(autouse=True)
def provider_boundary():
    app.state.razorpay_client_factory=lambda:gateway

def post(c,path,body=None):return c.post(path,headers=headers(c),json=body)
def buyer():return customer('rzp-'+secrets.token_hex(8)+'@example.com')
def operator():
    email='admin-'+secrets.token_hex(8)+'@example.com';create_admin(app.state.engine,app.state.identity_metadata,email,PASSWORD)
    c=TestClient(app,base_url=ORIGIN,client=('127.0.0.1',50000))
    assert post(c,'/api/auth/login',{'email':email,'password':PASSWORD}).status_code==200
    return c
def order(c,aid):
    assert add(c,'PACK-OLIVE-18').status_code==200
    made=post(c,'/api/orders',request(c,aid));assert made.status_code==201,made.text
    return made.json()
def endpoint(o,action,admin=False):return '/api/'+('admin/' if admin else '')+'razorpay/orders/'+str(o['id'])+'/'+action
def start(c,o):
    value=post(c,endpoint(o,'checkout'));assert value.status_code==200,value.text
    assert value.json()['amount']==o['total_minor'] and value.json()['mode']=='razorpay_test'
    return value.json()['order_id']
def callback(oid,pid):return {'razorpay_order_id':oid,'razorpay_payment_id':pid,'razorpay_signature':sign((oid+'|'+pid).encode())}
def event(c,oid,kind='order.paid',eid=None,account='acc_SYNTHETIC'):
    raw=json.dumps({'account_id':account,'event':kind,'payload':{'order':{'entity':{'id':oid}}}}).encode()
    return c.post('/api/razorpay/webhook',content=raw,headers={'x-razorpay-event-id':eid or secrets.token_hex(12),'x-razorpay-signature':sign(raw,WEBHOOK),'Content-Type':'application/json'})

def test_unconfigured_live_guard_and_authority():
    c,aid=buyer();o=order(c,aid)
    app.state.razorpay_client_factory=RazorpayTestClient.from_environment
    assert post(c,endpoint(o,'checkout')).status_code==503
    with pytest.raises(ProviderUnavailable):RazorpayTestClient('rzp_live_DISALLOWED',SECRET,WEBHOOK,'acc_SYNTHETIC')
    app.state.razorpay_client_factory=lambda:gateway
    other,_=buyer()
    assert post(other,endpoint(o,'checkout')).status_code==404
    assert c.post(endpoint(o,'checkout')).status_code==403
    assert post(c,endpoint(o,'refund',True),{'idempotency_key':secrets.token_hex(16)}).status_code==403
    assert c.get('/api/orders/'+str(o['id'])).json()['payment_status']=='not_started'
    assert post(c,'/api/orders/'+str(o['id'])+'/cancel').status_code==200

def test_signatures_amount_currency_and_capture_authority():
    c,aid=buyer();o=order(c,aid);before=stock('PACK-OLIVE-18');oid=start(c,o);pid=gateway.pay(oid,'authorized');body=callback(oid,pid)
    assert post(c,endpoint(o,'verify'),{**body,'razorpay_signature':'0'*64}).status_code==400
    assert post(c,endpoint(o,'verify'),{**body,'paid':True}).status_code==422
    assert post(c,endpoint(o,'verify'),body).json()['payment_status']=='authorized'
    assert c.get('/api/orders/'+str(o['id'])).json()['state']=='awaiting_payment'
    p=gateway.pays[pid];p.update(status='captured',captured=True);gateway.orders[oid]['status']='paid'
    for field,bad in [('amount',1),('currency','USD'),('order_id','order_WRONG'),('captured',False)]:
        old=p[field];p[field]=bad
        assert post(c,endpoint(o,'verify'),body).status_code==409
        p[field]=old
    assert post(c,endpoint(o,'verify'),body).json()['order_state']=='razorpay_test_paid'
    assert post(c,endpoint(o,'verify'),body).json()['payment_status']=='captured'
    assert stock('PACK-OLIVE-18')==before
    assert post(c,'/api/orders/'+str(o['id'])+'/cancel').status_code==409

def test_lost_order_create_is_reconciled_without_duplicate():
    c,aid=buyer();o=order(c,aid);count=gateway.creates;gateway.lost_create=True
    assert post(c,endpoint(o,'checkout')).status_code==503
    assert c.get('/api/orders/'+str(o['id'])).json()['payment_status']=='creating'
    oid=start(c,o);assert gateway.creates==count+1
    assert start(c,o)==oid and gateway.creates==count+1
    post(c,'/api/orders/'+str(o['id'])+'/cancel')

def test_webhook_invalid_duplicate_account_and_delayed_ordering():
    c,aid=buyer();o=order(c,aid);oid=start(c,o);pid=gateway.pay(oid,'failed')
    assert post(c,endpoint(o,'reconcile')).json()['payment_status']=='failed'
    assert c.post('/api/razorpay/webhook',content=b'{}',headers={'x-razorpay-event-id':'bad','x-razorpay-signature':'0'*64}).status_code==400
    assert event(c,oid,account='acc_WRONG').status_code==400
    pid=gateway.pay(oid);eid=secrets.token_hex(12)
    assert event(c,oid,eid=eid).status_code==200
    assert event(c,oid,eid=eid).json()['duplicate'] is True
    assert event(c,oid,kind='payment.failed',eid=eid).status_code==409
    raw=json.dumps({'account_id':gateway.account_id,'event':'payment.failed','payload':{'payment':{'entity':{'order_id':oid}}}}).encode()
    response=c.post('/api/razorpay/webhook',content=raw,headers={'x-razorpay-event-id':secrets.token_hex(12),'x-razorpay-signature':sign(raw,WEBHOOK)})
    assert response.status_code==200,response.text
    assert c.get('/api/orders/'+str(o['id'])).json()['state']=='razorpay_test_paid'

@pytest.mark.parametrize('terminal',['cancel','expire'])
def test_late_capture_never_reclaims_released_stock_and_refund_once(terminal):
    c,aid=buyer();before=stock('PACK-OLIVE-18');o=order(c,aid);oid=start(c,o)
    if terminal=='cancel':assert post(c,'/api/orders/'+str(o['id'])+'/cancel').status_code==200
    else:
        with app.state.engine.begin() as db:db.execute(text('UPDATE orders SET expires_at=0 WHERE id=:id'),{'id':o['id']})
        app.state.expire_reservations()
    pid=gateway.pay(oid)
    assert post(c,endpoint(o,'verify'),callback(oid,pid)).json()['payment_status']=='late_capture'
    assert stock('PACK-OLIVE-18')==before
    admin=operator();body={'idempotency_key':secrets.token_hex(16)}
    r=post(admin,endpoint(o,'refund',True),body);assert r.status_code==200,r.text
    rid=r.json()['provider_refunds'][0]['provider_id'];gateway.refunds[rid]['status']='processed'
    for _ in range(2):assert post(admin,endpoint(o,'reconcile',True)).json()['payment_status']=='refunded'
    assert stock('PACK-OLIVE-18')==before

def test_refund_lost_response_stable_key_pending_processed_replay():
    c,aid=buyer();before=stock('PACK-OLIVE-18');o=order(c,aid);oid=start(c,o);pid=gateway.pay(oid)
    assert post(c,endpoint(o,'verify'),callback(oid,pid)).status_code==200
    admin=operator();body={'idempotency_key':secrets.token_hex(16)};gateway.lost_refund=True
    assert post(admin,endpoint(o,'refund',True),body).status_code==503
    assert post(admin,endpoint(o,'refund',True),{'idempotency_key':secrets.token_hex(16)}).status_code==409
    r=post(admin,endpoint(o,'refund',True),body);assert r.status_code==200,r.text
    assert gateway.refund_calls[-1]==gateway.refund_calls[-2]
    rid=r.json()['provider_refunds'][0]['provider_id'];assert stock('PACK-OLIVE-18')==before-1
    gateway.refunds[rid]['status']='processed'
    for _ in range(2):assert post(admin,endpoint(o,'reconcile',True)).json()['payment_status']=='refunded'
    assert stock('PACK-OLIVE-18')==before
    # A delayed pending response cannot undo a completed refund.
    gateway.refunds[rid]['status']='pending'
    assert post(admin,endpoint(o,'reconcile',True)).json()['payment_status']=='refunded'
    assert stock('PACK-OLIVE-18')==before

def test_external_refund_flags_review_without_silent_restock():
    c,aid=buyer();o=order(c,aid);before=stock('PACK-OLIVE-18');oid=start(c,o);pid=gateway.pay(oid)
    assert post(c,endpoint(o,'verify'),callback(oid,pid)).status_code==200
    gateway.pays[pid]['amount_refunded']=o['total_minor']
    assert post(c,endpoint(o,'reconcile')).json()['payment_status']=='review'
    assert stock('PACK-OLIVE-18')==before

def test_saved_payment_survives_new_server_process():
    c,aid=buyer();o=order(c,aid);oid=start(c,o);pid=gateway.pay(oid)
    assert post(c,endpoint(o,'verify'),callback(oid,pid)).status_code==200
    server=subprocess.Popen(['python','-m','uvicorn','app.main:app','--host','127.0.0.1','--port','8012'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    try:
        for _ in range(80):
            try:
                if httpx.get('http://127.0.0.1:8012/api/store').status_code==200:break
            except httpx.HTTPError:pass
            time.sleep(.1)
        else:raise AssertionError('Restart failed')
        with httpx.Client(base_url='http://127.0.0.1:8012',cookies=dict(c.cookies)) as remote:
            r=remote.get('/api/orders/'+str(o['id']));assert r.status_code==200,r.text
            assert r.json()['payment_status']=='captured' and r.json()['state']=='razorpay_test_paid'
    finally:server.terminate();server.wait(timeout=5)

def test_failed_refund_retry_and_signed_notification():
    c,aid=buyer();before=stock('PACK-OLIVE-18');o=order(c,aid);oid=start(c,o);pid=gateway.pay(oid)
    assert post(c,endpoint(o,'verify'),callback(oid,pid)).status_code==200
    admin=operator();url=endpoint(o,'refund',True);body={'idempotency_key':secrets.token_hex(16)}
    r=post(admin,url,body);assert r.status_code==200,r.text
    rid=r.json()['provider_refunds'][-1]['provider_id'];gateway.refunds[rid]['status']='failed'
    assert post(admin,endpoint(o,'reconcile',True)).json()['provider_refunds'][-1]['state']=='failed'
    assert stock('PACK-OLIVE-18')==before-1
    # Definite failure permits a new request; unknown results must keep the original key.
    r=post(admin,url,{'idempotency_key':secrets.token_hex(16)});assert r.status_code==200,r.text
    rid=r.json()['provider_refunds'][-1]['provider_id'];gateway.refunds[rid]['status']='processed'
    raw=json.dumps({'account_id':gateway.account_id,'event':'refund.processed','payload':{'refund':{'entity':{'id':rid}}}}).encode()
    h={'x-razorpay-event-id':secrets.token_hex(12),'x-razorpay-signature':sign(raw,WEBHOOK)}
    assert c.post('/api/razorpay/webhook',content=raw,headers={**h,'x-razorpay-signature':'0'*64}).status_code==400
    assert stock('PACK-OLIVE-18')==before-1
    assert c.post('/api/razorpay/webhook',content=raw,headers=h).status_code==200
    assert c.post('/api/razorpay/webhook',content=raw,headers=h).json()['duplicate'] is True
    assert stock('PACK-OLIVE-18')==before

def test_refund_recovery_from_another_admin_session_uses_persisted_key():
    c,aid=buyer();o=order(c,aid);oid=start(c,o);pid=gateway.pay(oid)
    assert post(c,endpoint(o,'verify'),callback(oid,pid)).status_code==200
    admin=operator();gateway.lost_refund=True
    assert post(admin,endpoint(o,'refund',True),{'idempotency_key':secrets.token_hex(16)}).status_code==503
    assert post(c,endpoint(o,'retry-refund',True)).status_code==403
    assert post(operator(),endpoint(o,'retry-refund',True)).status_code==200
    assert gateway.refund_calls[-1]==gateway.refund_calls[-2]
    assert post(admin,endpoint(o,'retry-refund',True)).status_code==409

def test_concurrent_callback_and_webhook_cannot_double_apply():
    c,aid=buyer();o=order(c,aid);oid=start(c,o);pid=gateway.pay(oid);before=stock('PACK-OLIVE-18')
    barrier=threading.Barrier(2);results=[]
    def deliver(i):
        local=TestClient(app,base_url=ORIGIN,client=('127.0.0.20',51000+i));local.cookies.update(dict(c.cookies))
        barrier.wait()
        response=post(local,endpoint(o,'verify'),callback(oid,pid)) if i==0 else event(local,oid)
        results.append(response.status_code)
    workers=[threading.Thread(target=deliver,args=(i,)) for i in range(2)]
    [w.start() for w in workers];[w.join(timeout=20) for w in workers]
    assert all(not w.is_alive() for w in workers) and results==[200,200],results
    assert stock('PACK-OLIVE-18')==before
    with app.state.engine.connect() as db:
        assert db.execute(text('SELECT count(*) FROM razorpay_bindings WHERE order_id=:id'),{'id':o['id']}).scalar_one()==1

def test_provider_action_rate_limit_persists_across_sessions():
    c,aid=buyer();o=order(c,aid)
    local=TestClient(app,base_url=ORIGIN,client=('127.0.0.40',52000));local.cookies.update(dict(c.cookies))
    for _ in range(20):assert post(local,endpoint(o,'checkout')).status_code==200
    limited=post(local,endpoint(o,'checkout'));assert limited.status_code==429 and 'Retry-After' in limited.headers
    another=TestClient(app,base_url=ORIGIN,client=('127.0.0.41',52001));another.cookies.update(dict(c.cookies))
    assert post(another,endpoint(o,'checkout')).status_code==429

def test_phase5_upgrade_preserves_orders_and_rejects_downgrade():
    from app.order_runtime import create_app as legacy
    from app.razorpay_runtime import create_app as provider
    dbname='upgrade_'+secrets.token_hex(5)
    with app.state.engine.connect().execution_options(isolation_level='AUTOCOMMIT') as conn:
        conn.execute(text('CREATE DATABASE '+dbname+' TEMPLATE template0 ENCODING '+"'UTF8'"))
    url=app.state.engine.url.set(database=dbname).render_as_string(hide_password=False)
    previous=legacy(database_url=url)
    with TestClient(previous,base_url=ORIGIN,client=('127.0.0.1',50000)) as c:
        email='upgrade@example.com'
        assert post(c,'/api/auth/register',{'email':email,'name':'Upgrade buyer','password':PASSWORD}).status_code==200
        assert post(c,'/api/auth/login',{'email':email,'password':PASSWORD}).status_code==200
        address={'label':'Test','full_name':'Buyer','line1':'1 Test road','line2':'','city':'Test','region':'Test','postal_code':'00001','country':'IN'}
        aid=post(c,'/api/account/addresses',address).json()['id'];o=order(c,aid);cookies=dict(c.cookies)
        assert o['payment_status']=='not_implemented'
    upgraded=provider(database_url=url,client_factory=lambda:gateway)
    with TestClient(upgraded,base_url=ORIGIN,client=('127.0.0.1',50000)) as c:
        c.cookies.update(cookies);saved=c.get('/api/orders/'+str(o['id'])).json()
        assert saved['items']==o['items'] and saved['total_minor']==o['total_minor'] and saved['address_snapshot']==o['address_snapshot']
        oid=start(c,saved);pid=gateway.pay(oid)
        assert post(c,endpoint(o,'verify'),callback(oid,pid)).json()['payment_status']=='captured'
        with upgraded.state.engine.connect() as db:
            assert sorted(db.execute(text('SELECT revision FROM projectforge_migrations')).scalars())==['0001','0002','0003','0004_razorpay_test','0005_delivery','0006_tracking']
    with pytest.raises(Exception):
        with TestClient(legacy(database_url=url)):pass


def test_test_provider_delivery_and_refund_exclusion():
    c,aid=buyer();o=order(c,aid);a=operator();oid=start(c,o);pid=gateway.pay(oid)
    path=f"/api/admin/orders/{o['id']}/fulfillment"
    body={'expected_status':'not_packed','status':'packed'}
    assert post(a,path,body).status_code==409
    assert post(a,f"/api/admin/orders/{o['id']}/shipping-details",{'expected_version':0,'courier_name':'Example Courier','tracking_number':'UNPAID'}).status_code==409
    assert post(c,endpoint(o,'verify'),callback(oid,pid)).status_code==200
    before=stock('PACK-OLIVE-18')
    tracking_path=f"/api/admin/orders/{o['id']}/shipping-details"
    tracking_body={'expected_version':0,'courier_name':'Example Test Courier','tracking_number':'RZP-DEMO-001'}
    assert post(c,tracking_path,tracking_body).status_code==403
    assert post(a,tracking_path,tracking_body).json()['shipping_details']['version']==1
    assert c.get('/api/orders/'+str(o['id'])).json()['fulfillment']['shipping_details']['tracking_number']=='RZP-DEMO-001'
    assert post(a,tracking_path,{**tracking_body,'tracking_number':'CONFLICT'}).status_code==409
    assert post(c,path,body).status_code==403
    assert post(a,path,body).json()['status']=='packed'
    assert post(a,endpoint(o,'refund',True),{'idempotency_key':secrets.token_hex(16)}).status_code==409
    assert stock('PACK-OLIVE-18')==before
    for previous,next_status in [('packed','shipped'),('shipped','delivered')]:
        assert post(a,path,{'expected_status':previous,'status':next_status}).json()['status']==next_status
    assert c.get('/api/orders/'+str(o['id'])).json()['fulfillment']['status']=='delivered'
