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
