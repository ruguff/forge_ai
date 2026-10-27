"""Owner-only shipment projections and customer-facing browser acceptance."""
from app.execution.sandbox.tracking_gate import SOURCE as TRACKING_SOURCE, BROWSER as TRACKING_BROWSER
from app.execution.sandbox.razorpay_gate import SOURCE as PROVIDER_SOURCE

CASES = r'''

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
'''

SOURCE = TRACKING_SOURCE + CASES
SOURCE += r'''

def test_customer_shipment_refund_hold_and_refunded_state():
    c,o,p=paid_order();a=operator();url=f"/api/orders/{o['id']}/shipment"
    refund=post(a,f"/api/admin/simulation/payments/{p['id']}/refund",key())
    assert refund.status_code==200
    assert c.get(url).json()['availability']=='on_hold'
    assert post(a,f"/api/admin/simulation/refunds/{refund.json()['id']}/resolve",{**key(),'outcome':'succeeded'}).status_code==200
    result=c.get(url).json()
    assert result['availability']=='refunded' and result['status']=='not_packed'
    assert [event['status'] for event in result['history']]==['placed']
'''
RAZORPAY_SOURCE = PROVIDER_SOURCE + CASES

BROWSER = TRACKING_BROWSER + r'''

def test_customer_shipment_browser():
    c,aid=buyer();o=order(c,aid);p=start(c,o);a=operator();oid=o['id']
    backend=subprocess.Popen(['python','-m','uvicorn','app.main:app','--host','127.0.0.1','--port','8001','--no-proxy-headers'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    frontend=subprocess.Popen(['/opt/frontend/node_modules/.bin/vite','--host','127.0.0.1','--port','3001'],cwd='frontend',stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    try:
        ready(ORIGIN);ready('http://127.0.0.1:8001/api/store')
        with sync_playwright() as pw:
            browser=pw.chromium.launch(headless=True)
            context=browser.new_context(viewport={'width':1440,'height':1000},permissions=['clipboard-read','clipboard-write'])
            context.add_cookies([{'name':k,'value':v,'url':ORIGIN} for k,v in dict(c.cookies).items()])
            page=context.new_page();page.goto(ORIGIN+'/orders')
            page.get_by_test_id(f'track-shipment-{oid}').click()
            expect(page.get_by_role('heading',name='Track your shipment')).to_be_visible()
            expect(page.get_by_test_id('shipment-summary')).to_have_text('Awaiting payment')
            expect(page.get_by_test_id('shipment-empty')).to_be_visible()
            assert post(c,f"/api/simulation/payments/{p['id']}/resolve",outcome(p)).status_code==200
            page.get_by_role('button',name='Refresh shipment',exact=True).click()
            expect(page.get_by_test_id('shipment-summary')).to_have_text('Awaiting packing')
            tracking='DEMO-'+('0123456789'*9)+'-END'
            assert post(a,f'/api/admin/orders/{oid}/shipping-details',{'expected_version':0,'courier_name':'Example Courier','tracking_number':tracking}).status_code==200
            for previous,target in [('not_packed','packed'),('packed','shipped')]:
                assert post(a,f'/api/admin/orders/{oid}/fulfillment',{'expected_status':previous,'status':target}).status_code==200
            page.get_by_role('button',name='Refresh shipment',exact=True).click()
            expect(page.get_by_test_id('shipment-summary')).to_have_text('Shipped')
            expect(page.get_by_test_id('shipment-number')).to_have_text(tracking)
            expect(page.get_by_test_id('shipment-timeline').locator('time')).to_have_count(3)
            expect(page.get_by_role('textbox')).to_have_count(0)
            page.get_by_role('button',name='Copy tracking number',exact=True).click()
            expect(page.get_by_text('Tracking number copied.',exact=True)).to_be_visible()
            assert page.evaluate('navigator.clipboard.readText()')==tracking
            print('SHIPMENT_DESKTOP_PNG='+base64.b64encode(page.screenshot(full_page=True)).decode())
            page.set_viewport_size({'width':390,'height':844})
            assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
            print('SHIPMENT_MOBILE_PNG='+base64.b64encode(page.screenshot(full_page=True)).decode())
            assert post(a,f'/api/admin/orders/{oid}/fulfillment',{'expected_status':'shipped','status':'delivered'}).status_code==200
            page.get_by_role('button',name='Refresh shipment',exact=True).click()
            expect(page.get_by_test_id('shipment-summary')).to_have_text('Delivered')
            expect(page.get_by_test_id('shipment-timeline').locator('time')).to_have_count(4)
            # A failed refresh must clear old customer data and offer a retry.
            page.route(f'**/api/orders/{oid}/shipment',lambda route:route.fulfill(status=503,body='Unavailable'))
            page.get_by_role('button',name='Refresh shipment',exact=True).click()
            expect(page.get_by_role('alert')).to_contain_text('unavailable')
            expect(page.get_by_test_id('shipment-number')).to_have_count(0)
            page.unroute(f'**/api/orders/{oid}/shipment')
            page.get_by_role('button',name='Try again',exact=True).click()
            expect(page.get_by_test_id('shipment-summary')).to_have_text('Delivered')
            other,_=buyer();context.clear_cookies()
            context.add_cookies([{'name':k,'value':v,'url':ORIGIN} for k,v in dict(other.cookies).items()])
            page.reload();expect(page.get_by_role('alert')).to_contain_text('Shipment not found')
            expect(page.get_by_test_id('shipment-number')).to_have_count(0)
            context.clear_cookies();page.reload()
            expect(page.get_by_role('alert')).to_contain_text('Sign in')
            page.goto(ORIGIN+'/orders/not-an-id/tracking')
            expect(page.get_by_role('alert')).to_contain_text('invalid')
            browser.close()
    finally:
        frontend.terminate();backend.terminate();frontend.wait(timeout=15);backend.wait(timeout=15)
'''
