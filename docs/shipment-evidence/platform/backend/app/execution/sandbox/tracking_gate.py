"""Independent acceptance cases for manually entered courier and tracking details."""
from app.execution.sandbox.fulfillment_gate import SOURCE as DELIVERY_SOURCE, BROWSER as DELIVERY_BROWSER

SOURCE = DELIVERY_SOURCE + r'''

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
'''

BROWSER = DELIVERY_BROWSER.replace('def test_admin_delivery_browser():','def test_admin_tracking_browser():')
BROWSER = BROWSER.replace("            for label in ('packed','shipped','delivered'):", '''            form=page.get_by_test_id(f"shipping-form-{o['id']}")
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
            for label in ('packed','shipped','delivered'):''')
BROWSER = BROWSER.replace("            page.reload();expect(status).to_have_text('Delivered')", "            page.reload();expect(status).to_have_text('Delivered')\n            expect(form).to_have_count(0)\n            expect(details).to_contain_text('DEMO-FINAL-003')")
BROWSER = BROWSER.replace("            browser.close()", '''            expect(customer_page.get_by_test_id(f"shipping-details-{o['id']}")).to_contain_text('DEMO-FINAL-003')
            expect(customer_page.get_by_test_id(f"shipping-form-{o['id']}")).to_have_count(0)
            print('TRACKING_CUSTOMER_PNG='+base64.b64encode(customer_page.screenshot(full_page=True)).decode())
            browser.close()''')
