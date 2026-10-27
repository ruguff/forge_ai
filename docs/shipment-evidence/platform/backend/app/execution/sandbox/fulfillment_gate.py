"""Independent delivery acceptance checks for the offline store demo."""
from app.execution.sandbox.payment_gate import SOURCE as PAYMENT_SOURCE

SOURCE = PAYMENT_SOURCE + '''

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
'''

BROWSER = SOURCE.split('def test_pending_success_amount_authority_duplicate_and_late_outcome():')[0] + '''
from playwright.sync_api import sync_playwright,expect
import base64

def ready(url):
    for _ in range(100):
        try:
            if httpx.get(url).status_code==200:return
        except Exception:pass
        time.sleep(.2)
    raise AssertionError('Server did not start')

def test_admin_delivery_browser():
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
            for label in ('packed','shipped','delivered'):
                page.get_by_role('button',name=f"Mark order #{o['id']} as {label}",exact=True).click()
                expect(status).to_have_text(label.capitalize())
            page.reload();expect(status).to_have_text('Delivered')
            print('DELIVERY_DESKTOP_PNG='+base64.b64encode(page.screenshot(full_page=True)).decode())
            page.set_viewport_size({'width':390,'height':844})
            assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
            print('DELIVERY_MOBILE_PNG='+base64.b64encode(page.screenshot(full_page=True)).decode())
            customer_context=browser.new_context()
            customer_context.add_cookies([{'name':k,'value':v,'url':ORIGIN} for k,v in dict(c.cookies).items()])
            customer_page=customer_context.new_page();customer_page.goto(ORIGIN+'/orders')
            expect(customer_page.get_by_test_id(f"delivery-status-{o['id']}")).to_have_text('Delivered')
            expect(customer_page.get_by_role('button',name=f"Mark order #{o['id']}",exact=False)).to_have_count(0)
            browser.close()
    finally:
        frontend.terminate();backend.terminate();frontend.wait(timeout=15);backend.wait(timeout=15)
'''
