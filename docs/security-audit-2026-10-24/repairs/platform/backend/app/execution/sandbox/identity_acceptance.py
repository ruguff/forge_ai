"""Frozen independent phase-4 contracts; never supplied as implementation input."""
POSTGRES_TEST='''import os,subprocess,time,secrets
import httpx,pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from app.main import app
from app.identity_runtime import create_admin
ORIGIN='http://127.0.0.1:3001'
PASSWORD=secrets.token_urlsafe(24)
def headers(c):return {'Origin':ORIGIN,'X-CSRF-Token':c.get('/api/auth/csrf').json()['csrf_token']}
def login(c,email,password=PASSWORD):return c.post('/api/auth/login',headers=headers(c),json={'email':email,'password':password})
def start():
    process=subprocess.Popen(['python','-m','uvicorn','app.main:app','--host','127.0.0.1','--port','8001','--no-proxy-headers'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    for _ in range(150):
        try:
            if httpx.get('http://127.0.0.1:8001/api/store').status_code==200:return process
        except httpx.HTTPError:pass
        if process.poll() is not None:raise AssertionError('Backend failed startup')
        time.sleep(.1)
    process.terminate();process.wait(timeout=5);raise AssertionError('Readiness timeout')
def test_real_postgresql_identity_security_restart_and_admin():
    assert app.state.engine.dialect.name=='postgresql'
    with TestClient(app,base_url=ORIGIN,client=('127.0.0.1',50000)) as c:
        create_admin(app.state.engine,app.state.identity_metadata,'operator@example.com',PASSWORD)
        body={'email':'customer@example.com','password':PASSWORD,'name':'Test customer'}
        assert c.post('/api/auth/register',headers=headers(c),json=body).status_code==200
        assert c.post('/api/auth/register',headers=headers(c),json={**body,'role':'admin'}).status_code==422
        assert login(c,body['email']).status_code==200
        assert c.get('/api/admin/products').status_code==403
        assert c.patch('/api/account',headers={'Origin':'https://evil.invalid'},json={'name':'attacker'}).status_code==403
        address={'label':'Home','full_name':'Test customer','line1':'1 Test road','line2':'','city':'Surat','region':'Gujarat','postal_code':'395001','country':'IN'}
        response=c.post('/api/account/addresses',headers=headers(c),json=address);assert response.status_code==201
        aid=response.json()['id'];customer_cookies=dict(c.cookies)
        c.cookies.clear()
        assert c.post('/api/auth/register',headers=headers(c),json={**body,'email':'other@example.com'}).status_code==200
        login(c,'other@example.com')
        assert c.put('/api/account/addresses/'+str(aid),headers=headers(c),json=address).status_code==404
        assert c.delete('/api/account/addresses/'+str(aid),headers=headers(c)).status_code==404
        c.cookies.clear();assert login(c,'operator@example.com').status_code==200
        row=c.get('/api/admin/products').json()[0]
        sku=row['product']['variants'][0]['sku']
        assert c.put('/api/admin/variants/'+sku+'/stock',headers=headers(c),json={'quantity':7,'expected_version':row['version']}).status_code==200
        assert c.put('/api/admin/variants/'+sku+'/stock',headers=headers(c),json={'quantity':999,'expected_version':row['version']}).status_code==409
        # A conflicting SKU rolls the whole product insert back.
        before=len(c.get('/api/admin/products').json())
        bad={**row['product'],'slug':'conflicting-copy'}
        assert c.post('/api/admin/products',headers=headers(c),json=bad).status_code==409
        assert len(c.get('/api/admin/products').json())==before
        audit=c.get('/api/admin/audit').text
        assert PASSWORD not in audit and 'password_hash' not in audit
        with app.state.engine.connect() as db:
            hashes=db.execute(text('SELECT password_hash FROM users')).scalars().all()
            assert all(x.startswith('scrypt$131072$8$1$') for x in hashes)
            assert db.execute(text('SELECT count(*) FROM projectforge_migrations')).scalar_one()==2
        with pytest.raises(IntegrityError),app.state.engine.begin() as db:
            db.execute(text("UPDATE users SET role='superuser'"))
    # New server process, same database: accounts, session and owned addresses persist.
    process=start()
    try:
        with httpx.Client(base_url='http://127.0.0.1:8001',cookies=customer_cookies) as c:
            assert c.get('/api/account').json()['email']=='customer@example.com'
            assert c.get('/api/account/addresses').json()[0]['id']==aid
            assert c.get('/api/products/trail-pack').json()['variants'][0]['available'] is True
            assert c.post('/api/auth/logout',headers=headers(c)).status_code==200
            c.cookies.update(customer_cookies);assert c.get('/api/account').status_code==401
    finally:process.terminate();process.wait(timeout=5)
'''

BROWSER_TEST='''import base64,json,os,secrets,subprocess,time,urllib.request
from pathlib import Path
from playwright.sync_api import sync_playwright,expect
ORIGIN='http://127.0.0.1:3001'
PASSWORD=secrets.token_urlsafe(24)
def ready(url):
    for _ in range(150):
        try:urllib.request.urlopen(url,timeout=1).close();return
        except Exception:time.sleep(.1)
    raise AssertionError('Preview failed to start')
def snapshot(page,label):
    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1'),'Horizontal overflow'
    print('IDENTITY_SCREENSHOT:'+label+':'+base64.b64encode(page.screenshot(full_page=True,animations='disabled')).decode(),flush=True)
def test_account_address_admin_and_responsive_pages():
    env={**os.environ,'SYNTHETIC_ADMIN_PASSWORD':PASSWORD}
    subprocess.run(['python','manage.py','create-admin','--email','browser-admin@example.com','--password-env','SYNTHETIC_ADMIN_PASSWORD'],cwd='backend',env=env,check=True)
    backend=subprocess.Popen(['python','-m','uvicorn','app.main:app','--host','127.0.0.1','--port','8001','--no-proxy-headers'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    frontend=subprocess.Popen(['/opt/frontend/node_modules/.bin/vite','--host','127.0.0.1','--port','3001'],cwd='frontend',stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    try:
        ready(ORIGIN);ready('http://127.0.0.1:8001/api/store')
        with sync_playwright() as p:
            browser=p.chromium.launch(headless=True);page=browser.new_page(viewport={'width':1440,'height':1000})
            errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
            page.goto(ORIGIN+'/account')
            page.get_by_role('button',name='Create account',exact=True).click()
            page.get_by_label('Email',exact=True).fill('browser@example.com')
            page.get_by_label('Your name',exact=True).fill('Demo student')
            page.get_by_test_id('identity-password').fill(PASSWORD)
            page.get_by_test_id('identity-submit').click()
            expect(page.get_by_test_id('identity-message')).to_contain_text('Continue to sign in')
            page.get_by_test_id('identity-email').focus();page.keyboard.press('Tab');expect(page.get_by_test_id('identity-password')).to_be_focused()
            page.get_by_test_id('identity-password').fill('deliberately incorrect password');page.keyboard.press('Enter')
            expect(page.get_by_test_id('identity-message')).to_contain_text('Email or password is incorrect')
            page.get_by_test_id('identity-password').fill(PASSWORD);page.keyboard.press('Enter')
            expect(page.get_by_role('heading',name='Welcome, Demo student')).to_be_visible()
            form=page.get_by_test_id('identity-address')
            for label,value in [('Full name','Demo student'),('Address line 1','10 Demo road'),('City','Surat'),('Region','Gujarat'),('Postal code','395001')]:form.get_by_label(label,exact=True).fill(value)
            form.get_by_role('button',name='Save address',exact=True).click()
            expect(form.get_by_text('10 Demo road, Surat 395001')).to_be_visible()
            snapshot(page,'desktop-account')
            page.set_viewport_size({'width':390,'height':844});snapshot(page,'mobile-account')
            page.reload();expect(page.get_by_role('heading',name='Welcome, Demo student')).to_be_visible()
            page.get_by_role('button',name='Edit Home',exact=True).click()
            page.get_by_label('City',exact=True).fill('Ahmedabad');page.get_by_role('button',name='Save address',exact=True).click()
            expect(page.get_by_text('10 Demo road, Ahmedabad 395001')).to_be_visible()
            page.get_by_role('button',name='Delete Home',exact=True).click()
            expect(page.get_by_text('No saved addresses yet.')).to_be_visible()
            page.goto(ORIGIN+'/admin');expect(page.get_by_role('heading',name='Administrator access required')).to_be_visible()
            page.goto(ORIGIN+'/account');page.get_by_role('button',name='Sign out',exact=True).click()
            page.get_by_test_id('identity-email').fill('browser-admin@example.com');page.get_by_test_id('identity-password').fill(PASSWORD);page.get_by_test_id('identity-submit').click()
            expect(page.get_by_role('heading',name='Welcome, Administrator')).to_be_visible()
            page.goto(ORIGIN+'/admin');expect(page.get_by_test_id('identity-admin')).to_be_visible()
            page.get_by_role('button',name='Edit The trail pack',exact=True).click()
            page.get_by_label('Name',exact=True).first.fill('Browser reviewed pack')
            page.get_by_role('button',name='Save product',exact=True).click()
            expect(page.get_by_role('button',name='Edit Browser reviewed pack',exact=True)).to_be_visible()
            # Create and archive through the real UI; never call APIs to fake a browser success.
            page.get_by_role('button',name='Add product',exact=True).click()
            page.get_by_label('Product slug',exact=True).fill('browser-created')
            page.get_by_label('Material',exact=True).fill('Canvas')
            page.get_by_label('Name',exact=True).first.fill('Browser created product')
            page.get_by_label('Description',exact=True).fill('An independently created browser test product.')
            page.get_by_label('SKU',exact=True).fill('BROWSER-CREATED-SKU')
            page.get_by_role('button',name='Save product',exact=True).click()
            expect(page.get_by_role('button',name='Edit Browser created product',exact=True)).to_be_visible()
            page.get_by_role('button',name='Archive product',exact=True).click()
            expect(page.get_by_test_id('identity-message')).to_contain_text('Product archived')
            page.get_by_role('button',name='Edit Browser reviewed pack',exact=True).click()
            page.set_viewport_size({'width':1440,'height':1000});snapshot(page,'desktop-admin')
            page.set_viewport_size({'width':390,'height':844});snapshot(page,'mobile-admin')
            for width in (1024,320):
                page.set_viewport_size({'width':width,'height':800});assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
            page.goto(ORIGIN+'/');expect(page.get_by_role('heading',name='Browser reviewed pack')).to_be_visible()
            assert not errors,errors
            assert page.evaluate('localStorage.length')==0,'Credentials must not be placed in localStorage'
            browser.close()
    finally:
        frontend.terminate();backend.terminate();frontend.wait(timeout=5);backend.wait(timeout=5)
'''
