"""Independent cart/order lifecycle assertions; no payment success fixture."""
import json,secrets
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from app.execution.agent.order_runtime import create_app
from app.execution.spec.order_contract import OrderContract
from app.execution.spec.identity_contract import IdentityContract
from app.execution.spec.catalogue_example import example_spec
from tests.test_identity_runtime import headers,register,login,ORIGIN

@pytest.fixture
def store(tmp_path):
    paths=[tmp_path/name for name in ('orders.json','identity.json','catalogue.json')]
    values=[OrderContract(tax_basis_points=500,shipping_minor=100,discount_basis_points=1000,policy_label='Synthetic test rules'),IdentityContract(public_origin=ORIGIN,allow_local_http=True),example_spec().catalogue_contract]
    for path,value in zip(paths,values):path.write_text(value.model_dump_json(),encoding='utf-8')
    clock=[2000000000];url='sqlite:///'+str(tmp_path/'orders.db')
    app=create_app(*paths,url,clock=lambda:clock[0],mail_sink=lambda *args:None)
    with TestClient(app,base_url=ORIGIN,client=('127.0.0.1',50000)) as c:
        register(c);login(c)
        data=dict(label='Home',full_name='Customer',line1='1 Main road',line2='',city='Surat',region='Gujarat',postal_code='395001',country='IN')
        aid=c.post('/api/account/addresses',headers=headers(c),json=data).json()['id']
        yield app,c,clock,aid,paths,url

def add(c,sku='PACK-OLIVE-18',quantity=1):
    version=c.get('/api/cart').json()['version']
    result=c.put('/api/cart/items/'+sku,headers=headers(c),json={'quantity':quantity,'expected_version':version})
    assert result.status_code==200,result.text
    return result.json()
def request(c,aid):
    cart=c.get('/api/cart').json()
    return {'address_id':aid,'cart_version':cart['version'],'quote_hash':cart['quote_hash'],'idempotency_key':secrets.token_urlsafe(24)}
def place(c,body):return c.post('/api/orders',headers=headers(c),json=body)
def stock(app):
    with app.state.engine.connect() as db:return db.execute(text("SELECT stock_quantity FROM variants WHERE sku='PACK-OLIVE-18'")).scalar_one()

def test_server_totals_idempotency_and_snapshots(store):
    app,c,clock,aid,*_=store
    quote=add(c,quantity=2)
    assert quote['subtotal_minor']==499800 and quote['discount_minor']==49980 and quote['tax_minor']==22491 and quote['total_minor']==472411
    body=request(c,aid)
    assert place(c,{**body,'total_minor':1}).status_code==422
    made=place(c,body);assert made.status_code==201,made.text
    order=made.json();assert order['state']=='awaiting_payment' and order['payment_status']=='not_implemented'
    assert stock(app)==10 and c.get('/api/cart').json()['items']==[]
    assert place(c,body).json()['id']==order['id'] and stock(app)==10
    assert place(c,{**body,'address_id':aid+1}).status_code==409
    with app.state.engine.begin() as db:
        db.execute(text("UPDATE products SET name='Changed name' WHERE slug='trail-pack'"))
        db.execute(text("UPDATE variants SET price_minor=1 WHERE sku='PACK-OLIVE-18'"))
        db.execute(text("UPDATE addresses SET city='Changed city'"))
    saved=c.get('/api/orders/'+str(order['id'])).json()
    assert saved['items'][0]['product_name']=='The trail pack' and saved['items'][0]['unit_price_minor']==249900
    assert saved['address_snapshot']['city']=='Surat' and saved['total_minor']==472411

def test_cancel_expiry_and_no_double_release(store):
    app,c,clock,aid,*_=store
    add(c);order=place(c,request(c,aid)).json();assert stock(app)==11
    for _ in range(2):assert c.post(f"/api/orders/{order['id']}/cancel",headers=headers(c)).json()['state']=='cancelled'
    assert stock(app)==12
    add(c);order=place(c,request(c,aid)).json();clock[0]+=901
    app.state.expire_reservations();app.state.expire_reservations()
    assert stock(app)==12
    assert c.get('/api/orders/'+str(order['id'])).json()['state']=='expired'

def test_quote_changes_cart_versions_and_owner_security(store):
    app,c,clock,aid,*_=store
    quote=add(c);body=request(c,aid)
    with app.state.engine.begin() as db:db.execute(text("UPDATE variants SET price_minor=99 WHERE sku='PACK-OLIVE-18'"))
    assert place(c,body).status_code==409 and stock(app)==12
    assert c.put('/api/cart/items/PACK-OLIVE-18',headers=headers(c),json={'quantity':1,'expected_version':0}).status_code==409
    order=place(c,request(c,aid)).json();owner=dict(c.cookies)
    c.cookies.clear();register(c,'other@example.com');login(c,'other@example.com')
    assert c.get('/api/cart').json()['items']==[]
    assert c.get('/api/orders').json()==[]
    assert c.get('/api/orders/'+str(order['id'])).status_code==404
    assert c.post(f"/api/orders/{order['id']}/cancel",headers=headers(c)).status_code==404
    add(c)
    assert place(c,request(c,aid)).status_code==404
    assert c.get('/api/admin/orders').status_code==403
    assert c.put('/api/cart/items/PACK-OLIVE-18',json={'quantity':1,'expected_version':1}).status_code==403

def test_stock_hidden_products_restart_and_migration(store):
    app,c,clock,aid,paths,url=store
    assert c.put('/api/cart/items/PACK-SAND-18',headers=headers(c),json={'quantity':1,'expected_version':0}).status_code==409
    add(c);order=place(c,request(c,aid)).json();saved=dict(c.cookies)
    second=create_app(*paths,url,clock=lambda:clock[0],mail_sink=lambda *args:None)
    with TestClient(second,base_url=ORIGIN,client=('127.0.0.1',50000)) as after:
        after.cookies.update(saved)
        assert after.get('/api/orders').json()[0]['id']==order['id']
        assert stock(second)==11
    with app.state.engine.connect() as db:assert db.execute(text('SELECT count(*) FROM projectforge_migrations')).scalar_one()==3
