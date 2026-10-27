"""Independent negative and positive contracts for the reviewed identity module."""
import json
from urllib.parse import urlsplit,parse_qs
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select,text
from app.execution.agent.identity_runtime import create_app,create_admin
from app.execution.spec.catalogue_example import example_spec
from app.execution.spec.identity_contract import IdentityContract

PASSWORD='A quiet river under the moon'
ORIGIN='http://127.0.0.1:3001'

@pytest.fixture
def environment(tmp_path):
    catalogue=tmp_path/'catalogue.json';identity=tmp_path/'identity.json'
    catalogue.write_text(example_spec().catalogue_contract.model_dump_json(),encoding='utf-8')
    identity.write_text(IdentityContract(public_origin=ORIGIN,allow_local_http=True).model_dump_json(),encoding='utf-8')
    clock=[2000000000];mail=[]
    app=create_app(identity,catalogue,'sqlite:///'+str(tmp_path/'store.db'),clock=lambda:clock[0],mail_sink=lambda email,url:mail.append((email,url)))
    with TestClient(app,base_url=ORIGIN,client=('127.0.0.1',50000)) as client:
        yield app,client,clock,mail,identity,catalogue,tmp_path

def headers(client):
    return {'Origin':ORIGIN,'X-CSRF-Token':client.get('/api/auth/csrf').json()['csrf_token']}

def register(client,email='one@example.com'):
    return client.post('/api/auth/register',headers=headers(client),json={'email':email,'password':PASSWORD,'name':'Student'})

def login(client,email='one@example.com',password=PASSWORD):
    return client.post('/api/auth/login',headers=headers(client),json={'email':email,'password':password})

def test_account_session_csrf_and_roles(environment):
    app,c,*_=environment
    assert c.get('/api/account').status_code==401
    h=headers(c);old=dict(c.cookies)
    assert c.post('/api/auth/register',json={'email':'one@example.com','password':PASSWORD,'name':'Student'}).status_code==403
    assert c.post('/api/auth/register',headers={**h,'Origin':'https://evil.invalid'},json={}).status_code in (403,422)
    assert c.post('/api/auth/register',headers=h,json={'email':'one@example.com','password':PASSWORD,'name':'Student','role':'admin'}).status_code==422
    assert register(c).status_code==200
    response=login(c);assert response.status_code==200
    assert response.json()['user']['role']=='customer'
    assert dict(c.cookies)!=old
    assert 'HttpOnly' in response.headers['set-cookie']
    assert c.get('/api/account').headers['cache-control']=='no-store'
    assert c.get('/api/admin/products').status_code==403
    assert c.post('/api/admin/products',headers=headers(c),json={}).status_code in (403,422)
    assert c.patch('/api/account',headers=headers(c),json={'name':'Updated'}).json()['name']=='Updated'
    authenticated=dict(c.cookies)
    assert c.post('/api/auth/logout',headers=headers(c)).status_code==200
    c.cookies.update(authenticated)
    assert c.get('/api/account').status_code==401
    c.cookies.clear();c.cookies.update(old)
    assert c.get('/api/account').status_code==401

def test_owner_addresses_and_validation(environment):
    app,c,*_=environment
    register(c);assert login(c).status_code==200
    address=dict(label='Home',full_name='Student',line1='10 Main road',line2='',city='Ahmedabad',region='Gujarat',postal_code='380001',country='IN')
    made=c.post('/api/account/addresses',headers=headers(c),json=address)
    assert made.status_code==201
    aid=made.json()['id'];first=dict(c.cookies)
    assert c.post('/api/account/addresses',headers=headers(c),json={**address,'user_id':999}).status_code==422
    c.cookies.clear();register(c,'two@example.com');login(c,'two@example.com')
    assert c.get('/api/account/addresses').json()==[]
    assert c.put(f'/api/account/addresses/{aid}',headers=headers(c),json=address).status_code==404
    assert c.delete(f'/api/account/addresses/{aid}',headers=headers(c)).status_code==404
    c.cookies.clear();c.cookies.update(first)
    assert c.put(f'/api/account/addresses/{aid}',headers=headers(c),json={**address,'city':'Surat'}).status_code==200
    assert c.delete(f'/api/account/addresses/{aid}',headers=headers(c)).status_code==204

def test_recovery_reuse_expiry_and_revocation(environment):
    app,c,clock,mail,*_=environment
    register(c);login(c);authenticated=dict(c.cookies)
    known=c.post('/api/auth/forgot-password',headers=headers(c),json={'email':'one@example.com'})
    unknown=c.post('/api/auth/forgot-password',headers=headers(c),json={'email':'missing@example.com'})
    assert known.json()==unknown.json() and len(mail)==1
    token=parse_qs(urlsplit(mail[0][1]).fragment)['token'][0]
    new='Another very long recovery passphrase'
    assert token not in known.text
    assert c.post('/api/auth/reset-password',headers=headers(c),json={'token':token,'password':new}).status_code==200
    c.cookies.clear();c.cookies.update(authenticated)
    assert c.get('/api/account').status_code==401
    assert c.post('/api/auth/reset-password',headers=headers(c),json={'token':token,'password':new}).status_code==400
    assert login(c,password=PASSWORD).status_code==401
    assert login(c,password=new).status_code==200
    c.post('/api/auth/forgot-password',headers=headers(c),json={'email':'one@example.com'})
    token=parse_qs(urlsplit(mail[-1][1]).fragment)['token'][0];clock[0]+=901
    assert c.post('/api/auth/reset-password',headers=headers(c),json={'token':token,'password':PASSWORD}).status_code==400
    with app.state.engine.connect() as db:
        stored=db.execute(text('select token_hash from password_resets')).scalars().all()
        assert token not in stored

def test_admin_transactions_stock_and_stale_versions(environment):
    app,c,*_=environment
    create_admin(app.state.engine,app.state.identity_metadata,'admin@example.com',PASSWORD)
    assert login(c,'admin@example.com').status_code==200
    items=c.get('/api/admin/products').json();row=items[0];product=row['product']
    changed=c.put(f"/api/admin/products/{row['id']}",headers=headers(c),json={'product':{**product,'name':'Reviewed pack'},'expected_version':row['version']})
    assert changed.status_code==200,changed.text
    assert c.put(f"/api/admin/products/{row['id']}",headers=headers(c),json={'product':product,'expected_version':row['version']}).status_code==409
    sku=product['variants'][0]['sku']
    assert c.put(f'/api/admin/variants/{sku}/stock',headers=headers(c),json={'quantity':3,'expected_version':changed.json()['version']}).status_code==200
    assert c.put(f'/api/admin/variants/{sku}/stock',headers=headers(c),json={'quantity':-1,'expected_version':3}).status_code==422
    copy={**product,'slug':'copy-pack','variants':[{**product['variants'][0],'sku':'COPY-PACK'}]}
    made=c.post('/api/admin/products',headers=headers(c),json=copy);assert made.status_code==201,made.text
    assert c.delete(f"/api/admin/products/{made.json()['id']}?expected_version=1",headers=headers(c)).status_code==204
    assert c.get('/api/products/copy-pack').status_code==404
    assert c.post('/api/admin/categories',headers=headers(c),json={'slug':'new-category','name':'New category','active':True}).status_code==201
    audit=c.get('/api/admin/audit');assert audit.status_code==200
    assert PASSWORD not in audit.text and 'password_hash' not in audit.text


def test_invalid_resets_cannot_lock_out_another_ip(environment):
    app,c,clock,mail,identity,catalogue,tmp_path=environment
    assert register(c).status_code==200
    assert c.post('/api/auth/forgot-password',headers=headers(c),json={'email':'one@example.com'}).status_code==200
    token=parse_qs(urlsplit(mail[-1][1]).fragment)['token'][0]
    attacker=TestClient(app,base_url=ORIGIN,client=('127.0.0.2',50001))
    h=headers(attacker)
    invalid={'token':'x'*43,'password':PASSWORD}
    for _ in range(40):
        assert attacker.post('/api/auth/reset-password',headers=h,json=invalid).status_code==400
    assert attacker.post('/api/auth/reset-password',headers=h,json=invalid).status_code==429
    # A new session/application cannot evade the persisted IP allowance.
    second=create_app(identity,catalogue,'sqlite:///'+str(tmp_path/'store.db'),clock=lambda:clock[0])
    with TestClient(second,base_url=ORIGIN,client=('127.0.0.2',50002)) as again:
        assert again.post('/api/auth/reset-password',headers=headers(again),json=invalid).status_code==429
    response=c.post('/api/auth/reset-password',headers=headers(c),json={'token':token,'password':'A fresh long recovery passphrase'})
    assert response.status_code==200,response.text
    assert login(c,password='A fresh long recovery passphrase').status_code==200
    assert c.post('/api/auth/reset-password',headers=headers(c),json={'token':token,'password':PASSWORD}).status_code==400
    clock[0]+=901
    assert attacker.post('/api/auth/reset-password',headers=headers(attacker),json=invalid).status_code==400

def test_rate_limit_survives_restart_and_migration(environment):
    app,c,clock,mail,identity,catalogue,tmp_path=environment
    for _ in range(8):assert login(c,'absent@example.com').status_code==401
    assert login(c,'absent@example.com').status_code==429
    second=create_app(identity,catalogue,'sqlite:///'+str(tmp_path/'store.db'),clock=lambda:clock[0])
    with TestClient(second,base_url=ORIGIN,client=('127.0.0.1',50000)) as other:
        assert login(other,'absent@example.com').status_code==429
        assert other.get('/api/products').json()['total']>0
    with app.state.engine.connect() as db:
        assert db.execute(text('select count(*) from projectforge_migrations')).scalar_one()==2

def test_idle_expiry_and_request_bounds(environment):
    app,c,clock,*_=environment
    register(c);login(c);clock[0]+=1801
    assert c.get('/api/account').status_code==401
    assert c.post('/api/auth/login',content='x'*65537).status_code==413
    with TestClient(app,base_url=ORIGIN,client=('192.0.2.1',50000)) as remote:
        assert remote.get('/api/store').status_code==403

def test_absolute_expiry_password_change_and_error_redaction(environment):
    app,c,clock,*_=environment
    register(c);login(c)
    for _ in range(19):
        clock[0]+=1500
        assert c.get('/api/account').status_code==200
    clock[0]+=301
    assert c.get('/api/account').status_code==401
    assert login(c).status_code==200
    old=dict(c.cookies)
    response=c.post('/api/account/password',headers=headers(c),json={'current_password':PASSWORD,'password':'A different long passphrase for testing'})
    assert response.status_code==200
    c.cookies.update(old);assert c.get('/api/account').status_code==401
    response=c.post('/api/auth/register',headers=headers(c),json={'email':'invalid','password':PASSWORD,'name':''})
    assert response.status_code==422 and PASSWORD not in response.text

def test_https_cookie_and_configuration(environment):
    app,c,clock,mail,identity,catalogue,tmp_path=environment
    identity.write_text(IdentityContract(public_origin='https://store.example.invalid').model_dump_json(),encoding='utf-8')
    secure=create_app(identity,catalogue,'sqlite:///'+str(tmp_path/'secure.db'))
    with TestClient(secure,base_url='https://store.example.invalid') as client:
        response=client.get('/api/auth/csrf')
        cookie=response.headers['set-cookie']
        assert '__Host-pf_session=' in cookie and 'Secure' in cookie and 'HttpOnly' in cookie and 'SameSite=lax' in cookie
        assert 'Domain=' not in cookie
    from pydantic import ValidationError
    for origin in ('http://public.example.com','https://user:pass@example.com','https://example.com/path'):
        with pytest.raises(ValidationError):IdentityContract(public_origin=origin)

def test_generation_is_explicit_and_does_not_downgrade_identity():
    from app.execution.agent.identity import prepare_spec,sources
    from app.execution.agent.catalogue import prepare_spec as catalogue_spec
    spec=example_spec();spec.identity_contract=IdentityContract();spec.tech_stack.auth_provider='session'
    with pytest.raises(ValueError):catalogue_spec(spec)
    result=prepare_spec(spec);generated=sources(result)
    assert result.source_generation_strategy=='IDENTITY'
    assert ('POST','/api/auth/login') in {(e.method,e.path) for e in result.api_endpoints}
    assert len(generated)<=40
    for path,source in generated.items():
        if path.endswith('.py'):compile(source,path,'exec')
    assert 'IDENTITY_SMTP_PASSWORD' not in generated['backend/app/identity.json']
    spec.requirements[0].description='Support checkout and payments'
    with pytest.raises(ValueError,match='exceeds'):prepare_spec(spec)


def test_local_recovery_outbox_is_server_only(environment,monkeypatch):
    app,c,clock,mail,identity,catalogue,tmp_path=environment
    register(c)
    outbox=tmp_path/'private-mail';monkeypatch.setenv('IDENTITY_OUTBOX_DIR',str(outbox))
    local=create_app(identity,catalogue,'sqlite:///'+str(tmp_path/'store.db'),clock=lambda:clock[0])
    with TestClient(local,base_url=ORIGIN,client=('127.0.0.1',50000)) as other:
        result=other.post('/api/auth/forgot-password',headers=headers(other),json={'email':'one@example.com'})
        assert result.status_code==200
        messages=list(outbox.glob('*.json'));assert len(messages)==1
        document=json.loads(messages[0].read_text(encoding='utf-8'))
        assert document['to']=='one@example.com'
        token=parse_qs(urlsplit(document['recovery_url']).fragment)['token'][0]
        assert token not in result.text
        assert other.get('/api/auth/outbox').status_code==404
        assert other.post('/api/auth/reset-password',headers=headers(other),json={'token':token,'password':'Local recovery replacement phrase'}).status_code==200
