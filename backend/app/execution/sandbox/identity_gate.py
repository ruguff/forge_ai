"""Mandatory, catalogue-independent identity gate for every generated IDENTITY app."""
SOURCE='''import json,secrets
from pathlib import Path
from fastapi.testclient import TestClient
from app.main import app
from app.identity_runtime import create_admin
ORIGIN=json.loads(Path('backend/app/identity.json').read_text())['public_origin']
PASSWORD=secrets.token_urlsafe(24)
EMAIL=secrets.token_hex(8)+'@example.com'
def headers(c):return {'Origin':ORIGIN,'X-CSRF-Token':c.get('/api/auth/csrf').json()['csrf_token']}
def test_platform_identity_authority_contract():
    with TestClient(app,base_url=ORIGIN,client=('127.0.0.1',50000)) as c:
        payload={'email':EMAIL,'name':'Contract customer','password':PASSWORD}
        assert c.get('/api/account').status_code==401
        assert c.post('/api/auth/register',headers=headers(c),json={**payload,'role':'admin'}).status_code==422
        assert c.post('/api/auth/register',headers=headers(c),json=payload).status_code==200
        before=dict(c.cookies)
        login=c.post('/api/auth/login',headers=headers(c),json={'email':EMAIL,'password':PASSWORD})
        assert login.status_code==200 and login.json()['user']['role']=='customer'
        assert dict(c.cookies)!=before
        assert 'HttpOnly' in login.headers['set-cookie']
        assert c.get('/api/admin/products').status_code==403
        assert c.patch('/api/account',headers={'Origin':'https://hostile.invalid'},json={'name':'forged'}).status_code==403
        assert c.patch('/api/account',headers=headers(c),json={'name':'Renamed customer'}).status_code==200
        data={'label':'Home','full_name':'Contract customer','line1':'Test street','line2':'','city':'Test city','region':'Test region','postal_code':'00001','country':'IN'}
        made=c.post('/api/account/addresses',headers=headers(c),json=data);assert made.status_code==201
        aid=made.json()['id'];saved=dict(c.cookies)
        c.cookies.clear()
        other={**payload,'email':'other-'+EMAIL}
        assert c.post('/api/auth/register',headers=headers(c),json=other).status_code==200
        assert c.post('/api/auth/login',headers=headers(c),json={'email':other['email'],'password':PASSWORD}).status_code==200
        assert c.get('/api/account/addresses').json()==[]
        assert c.put('/api/account/addresses/'+str(aid),headers=headers(c),json=data).status_code==404
        assert c.delete('/api/account/addresses/'+str(aid),headers=headers(c)).status_code==404
        c.cookies.clear();c.cookies.update(saved)
        assert c.delete('/api/account/addresses/'+str(aid),headers=headers(c)).status_code==204
        assert c.post('/api/auth/logout',headers=headers(c)).status_code==200
        c.cookies.update(saved);assert c.get('/api/account').status_code==401
        operator='admin-'+EMAIL;create_admin(app.state.engine,app.state.identity_metadata,operator,PASSWORD)
        c.cookies.clear()
        assert c.post('/api/auth/login',headers=headers(c),json={'email':operator,'password':PASSWORD}).status_code==200
        assert c.get('/api/admin/products').status_code==200
        assert c.get('/api/admin/audit').status_code==200
'''
