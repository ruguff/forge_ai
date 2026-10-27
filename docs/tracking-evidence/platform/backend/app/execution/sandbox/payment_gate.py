"""Independent simulator contract v1. No provider integration is claimed."""
from app.execution.sandbox.order_gate import SOURCE as ORDER_SOURCE

SOURCE = ORDER_SOURCE.split('def test_order_module_server_price_idempotency_cancel_and_owner():')[0] + '''
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
'''

SOURCE += '''
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
'''
