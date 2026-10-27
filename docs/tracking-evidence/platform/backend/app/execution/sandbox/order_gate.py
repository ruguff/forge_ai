"""Independent phase-5 invariants exercised in every generated ORDERS build."""
SOURCE='''import json,secrets,threading,subprocess,time
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
def test_order_module_server_price_idempotency_cancel_and_owner():
    c,aid=customer('buyer-'+secrets.token_hex(5)+'@example.com')
    quote=add(c,'PACK-OLIVE-18',2);assert quote.status_code==200
    q=quote.json();assert q['subtotal_minor']==499800 and q['total_minor']==q['subtotal_minor']-q['discount_minor']+q['tax_minor']+q['shipping_minor']
    body=request(c,aid);before=stock('PACK-OLIVE-18')
    assert c.post('/api/orders',headers=headers(c),json={**body,'total_minor':1}).status_code==422
    placed=c.post('/api/orders',headers=headers(c),json=body);assert placed.status_code==201,placed.text
    order=placed.json();assert order['state']=='awaiting_payment'
    assert order['payment_status']==('not_started' if getattr(app.state,'payment_simulator',False) or getattr(app.state,'razorpay_test',False) else 'not_implemented')
    assert stock('PACK-OLIVE-18')==before-2 and c.get('/api/cart').json()['items']==[]
    assert c.post('/api/orders',headers=headers(c),json=body).json()['id']==order['id']
    assert stock('PACK-OLIVE-18')==before-2
    assert c.post('/api/orders',headers=headers(c),json={**body,'address_id':aid+100000}).status_code==409
    with app.state.engine.begin() as db:
        db.execute(text("UPDATE variants SET price_minor=1 WHERE sku='PACK-OLIVE-18'"))
        db.execute(text("UPDATE products SET name='Changed after sale' WHERE slug='trail-pack'"))
        db.execute(text("UPDATE addresses SET city='Changed after sale' WHERE id=:id"),{'id':aid})
    saved=c.get('/api/orders/'+str(order['id'])).json()
    assert saved['items'][0]['unit_price_minor']>1 and saved['items'][0]['product_name']!='Changed after sale'
    assert saved['address_snapshot']['city']=='Test city'
    assert c.post('/api/orders/'+str(order['id'])+'/cancel',headers=headers(c)).json()['state']=='cancelled'
    assert c.post('/api/orders/'+str(order['id'])+'/cancel',headers=headers(c)).json()['state']=='cancelled'
    assert stock('PACK-OLIVE-18')==before
    other,other_address=customer('other-'+secrets.token_hex(5)+'@example.com')
    assert other.get('/api/orders').json()==[]
    assert other.get('/api/orders/'+str(order['id'])).status_code==404
    assert other.post('/api/orders/'+str(order['id'])+'/cancel',headers=headers(other)).status_code==404
    assert other.get('/api/admin/orders').status_code==403
def test_expiry_releases_once_and_stale_quote_is_rejected():
    c,aid=customer('expiry-'+secrets.token_hex(5)+'@example.com')
    assert add(c,'PACK-OLIVE-18').status_code==200
    body=request(c,aid);key=body['idempotency_key'];quote=c.get('/api/cart').json()
    with app.state.engine.begin() as db:db.execute(text("UPDATE variants SET price_minor=price_minor+1 WHERE sku='PACK-OLIVE-18'"))
    assert c.post('/api/orders',headers=headers(c),json=body).status_code==409
    assert add(c,'PACK-SAND-18').status_code==409
    fresh_quote=c.get('/api/cart').json()
    assert fresh_quote['can_checkout'] is True
    assert [item['sku'] for item in fresh_quote['items']]==['PACK-OLIVE-18']
    with app.state.engine.begin() as db:db.execute(text("UPDATE variants SET price_minor=price_minor-1,stock_quantity=stock_quantity+1 WHERE sku='PACK-OLIVE-18'"))
    fresh=request(c,aid);placed=c.post('/api/orders',headers=headers(c),json=fresh);assert placed.status_code==201
    before=stock('PACK-OLIVE-18')
    with app.state.engine.begin() as db:db.execute(text("UPDATE orders SET expires_at=0 WHERE id=:id"),{'id':placed.json()['id']})
    app.state.expire_reservations();app.state.expire_reservations()
    assert stock('PACK-OLIVE-18')==before+1
    assert c.get('/api/orders/'+str(placed.json()['id'])).json()['state']=='expired'
def test_concurrent_orders_cannot_oversell():
    with app.state.engine.begin() as db:
        db.execute(text("UPDATE variants SET stock_quantity=1,price_minor=249900 WHERE sku='PACK-OLIVE-18'"))
        db.execute(text("UPDATE products SET name='The trail pack' WHERE slug='trail-pack'"))
    first,first_address=customer('race-a-'+secrets.token_hex(5)+'@example.com')
    second,second_address=customer('race-b-'+secrets.token_hex(5)+'@example.com')
    assert add(first,'PACK-OLIVE-18').status_code==200 and add(second,'PACK-OLIVE-18').status_code==200
    bodies=[request(first,first_address),request(second,second_address)]
    cookies=[dict(first.cookies),dict(second.cookies)]
    origins=[ORIGIN,ORIGIN];barrier=threading.Barrier(2);results=[]
    def place(i):
        # Each thread owns its TestClient/ASGI portal; only persisted cookies are shared.
        client=TestClient(app,base_url=origins[i],client=('127.0.0.1',50000+i))
        client.cookies.update(cookies[i])
        barrier.wait()
        results.append(client.post('/api/orders',headers=headers(client),json=bodies[i]).status_code)
    workers=[threading.Thread(target=place,args=(i,)) for i in range(2)]
    [w.start() for w in workers];[w.join(timeout=25) for w in workers]
    assert all(not w.is_alive() for w in workers)
    assert sorted(results)==[201,409],results
    assert stock('PACK-OLIVE-18')==0
def test_order_and_reservation_survive_backend_process_restart():
    with app.state.engine.begin() as db:
        db.execute(text("UPDATE variants SET stock_quantity=3,price_minor=249900 WHERE sku='PACK-OLIVE-18'"))
    c,aid=customer('restart-'+secrets.token_hex(5)+'@example.com')
    assert add(c,'PACK-OLIVE-18').status_code==200
    placed=c.post('/api/orders',headers=headers(c),json=request(c,aid));assert placed.status_code==201,placed.text
    oid=placed.json()['id'];cookies=dict(c.cookies)
    def start(port):
        process=subprocess.Popen(['python','-m','uvicorn','app.main:app','--host','127.0.0.1','--port',str(port),'--no-proxy-headers'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        for _ in range(150):
            try:
                if httpx.get('http://127.0.0.1:'+str(port)+'/api/store',timeout=1).status_code==200:return process
            except httpx.HTTPError:pass
            if process.poll() is not None:raise AssertionError('Backend process failed to start')
            time.sleep(.1)
        process.terminate();process.wait(timeout=5);raise AssertionError('Backend process readiness timeout')
    for port in (8002,8003):
        process=start(port)
        try:
            with httpx.Client(base_url='http://127.0.0.1:'+str(port),cookies=cookies) as client:
                rows=client.get('/api/orders').json()
                assert any(row['id']==oid and row['state']=='awaiting_payment' for row in rows),rows
            assert stock('PACK-OLIVE-18')==2
        finally:
            process.terminate();process.wait(timeout=5)
'''
