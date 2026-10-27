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


from playwright.sync_api import sync_playwright,expect
import base64

def ready(url):
    for _ in range(100):
        try:
            if httpx.get(url).status_code==200:return
        except Exception:pass
        time.sleep(.2)
    raise AssertionError('Server did not start')

def test_admin_tracking_browser():
    c,aid=buyer();o=order(c,aid);p=start(c,o);a=operator()
    assert post(c,f"/api/simulation/payments/{p['id']}/resolve",outcome(p)).status_code==200
    backend=subprocess.Popen(['python','-m','uvicorn','app.main:app','--host','127.0.0.1','--port','8001','--no-proxy-headers'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    frontend=subprocess.Popen(['/opt/frontend/node_modules/.bin/vite','--host','127.0.0.1','--port','3001'],cwd='frontend',stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    try:
        ready(ORIGIN);ready('http://127.0.0.1:8001/api/store')
        with sync_playwright() as pw:
            browser=pw.chromium.launch(headless=True)
            context=browser.new_context(viewport={'width':1440,'height':1000})
            context.add_cookies([{'name':k,'value':v,'url':ORIGIN} for k,v in dict(a.cookies).items()])
            page=context.new_page();page.goto(ORIGIN+'/admin/orders')
            status=page.get_by_test_id(f"delivery-status-{o['id']}")
            expect(status).to_have_text('Not packed')
            form=page.get_by_test_id(f"shipping-form-{o['id']}")
            expect(form).to_be_visible()
            form.get_by_label('Courier name',exact=True).fill('Example Courier')
            form.get_by_label('Tracking number',exact=True).fill('DEMO-TRACK-001')
            form.get_by_role('button',name=f"Save shipping details for order #{o['id']}",exact=True).click()
            details=page.get_by_test_id(f"shipping-details-{o['id']}")
            expect(details).to_contain_text('DEMO-TRACK-001')
            page.reload();expect(form.get_by_label('Tracking number',exact=True)).to_have_value('DEMO-TRACK-001')
            # Exercise a stale browser edit using a second authenticated admin request.
            changed=post(a,f"/api/admin/orders/{o['id']}/shipping-details",{'expected_version':1,'courier_name':'Second Courier','tracking_number':'DEMO-002'})
            assert changed.status_code==200
            form.get_by_label('Tracking number',exact=True).fill('STALE-EDIT')
            form.get_by_role('button',name=f"Save shipping details for order #{o['id']}",exact=True).click()
            expect(page.get_by_role('alert')).to_contain_text('Shipping details changed')
            page.get_by_role('button',name=f"Refresh order #{o['id']}",exact=True).click()
            expect(form.get_by_label('Tracking number',exact=True)).to_have_value('DEMO-002')
            form.get_by_label('Tracking number',exact=True).fill('DEMO-FINAL-003')
            form.get_by_role('button',name=f"Save shipping details for order #{o['id']}",exact=True).click()
            expect(details).to_contain_text('DEMO-FINAL-003')
            print('TRACKING_FORM_DESKTOP_PNG='+base64.b64encode(page.screenshot(full_page=True)).decode())
            page.set_viewport_size({'width':390,'height':844})
            assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
            print('TRACKING_FORM_MOBILE_PNG='+base64.b64encode(page.screenshot(full_page=True)).decode())
            page.set_viewport_size({'width':1440,'height':1000})
            for label in ('packed','shipped','delivered'):
                page.get_by_role('button',name=f"Mark order #{o['id']} as {label}",exact=True).click()
                expect(status).to_have_text(label.capitalize())
            page.reload();expect(status).to_have_text('Delivered')
            expect(form).to_have_count(0)
            expect(details).to_contain_text('DEMO-FINAL-003')
            print('DELIVERY_DESKTOP_PNG='+base64.b64encode(page.screenshot(full_page=True)).decode())
            page.set_viewport_size({'width':390,'height':844})
            assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
            print('DELIVERY_MOBILE_PNG='+base64.b64encode(page.screenshot(full_page=True)).decode())
            customer_context=browser.new_context()
            customer_context.add_cookies([{'name':k,'value':v,'url':ORIGIN} for k,v in dict(c.cookies).items()])
            customer_page=customer_context.new_page();customer_page.goto(ORIGIN+'/orders')
            expect(customer_page.get_by_test_id(f"delivery-status-{o['id']}")).to_have_text('Delivered')
            expect(customer_page.get_by_role('button',name=f"Mark order #{o['id']}",exact=False)).to_have_count(0)
            expect(customer_page.get_by_test_id(f"shipping-details-{o['id']}")).to_contain_text('DEMO-FINAL-003')
            expect(customer_page.get_by_test_id(f"shipping-form-{o['id']}")).to_have_count(0)
            print('TRACKING_CUSTOMER_PNG='+base64.b64encode(customer_page.screenshot(full_page=True)).decode())
            browser.close()
    finally:
        frontend.terminate();backend.terminate();frontend.wait(timeout=15);backend.wait(timeout=15)
