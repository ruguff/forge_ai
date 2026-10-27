"""Reviewed account/session module. Server authority, CSRF and explicit ownership."""
import hashlib
import hmac
import ipaddress
import json
import os
import secrets
import smtplib
import tempfile
import threading
import time
from contextlib import asynccontextmanager
from email.message import EmailMessage
from pathlib import Path
from urllib.parse import urlsplit
from fastapi import Request,Response,HTTPException,BackgroundTasks
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy import (MetaData,Table,Column,Integer,Text,Boolean,ForeignKey,CheckConstraint,
                        select,update,delete,insert,text,inspect)
from sqlalchemy.exc import IntegrityError
from .identity_models import Credentials,Register,Forgot,Reset,ChangePassword,Profile,Address,AdminProduct,ProductUpdate,StockUpdate,CategoryInput
from .catalogue_runtime import create_app as catalogue_app
try:
    from .identity_contract import IdentityContract
except ModuleNotFoundError:
    from app.execution.spec.identity_contract import IdentityContract

MIGRATION={'revision':'0002','parent':'0001','module':'identity-v1','schema_version':1,
    'tables':['users','sessions','password_resets','addresses','rate_limits','audit_records'],
    'catalogue_additions':['products.version:integer:not-null:default-1']}
MIGRATION_HASH=hashlib.sha256(json.dumps(MIGRATION,sort_keys=True).encode()).hexdigest()
HASH_GATE=threading.Semaphore(1)


def digest(value):return hashlib.sha256(value.encode()).hexdigest()


def hash_password(password):
    salt=secrets.token_bytes(16)
    with HASH_GATE:
        value=hashlib.scrypt(password.encode(),salt=salt,n=131072,r=8,p=1,dklen=32,maxmem=256*1024*1024)
    return 'scrypt$131072$8$1$'+salt.hex()+'$'+value.hex()


def verify_password(password,encoded):
    try:
        algorithm,n,r,p,salt,value=encoded.split('$')
        if (algorithm,n,r,p)!=('scrypt','131072','8','1') or len(salt)!=32 or len(value)!=64:return False
        with HASH_GATE:
            calculated=hashlib.scrypt(password.encode(),salt=bytes.fromhex(salt),n=131072,r=8,p=1,dklen=32,maxmem=256*1024*1024)
        return hmac.compare_digest(calculated,bytes.fromhex(value))
    except (ValueError,TypeError):return False


def identity_metadata():
    m=MetaData()
    Table('users',m,Column('id',Integer,primary_key=True),Column('email',Text,nullable=False,unique=True),
        Column('name',Text,nullable=False),Column('password_hash',Text,nullable=False),Column('role',Text,nullable=False),
        Column('active',Boolean,nullable=False),Column('auth_epoch',Integer,nullable=False),Column('created_at',Integer,nullable=False),
        CheckConstraint("role IN ('customer','admin')",name='allowed_identity_role'))
    Table('sessions',m,Column('id_hash',Text,primary_key=True),Column('user_id',Integer,ForeignKey('users.id',ondelete='CASCADE'),index=True),
        Column('csrf',Text,nullable=False),Column('auth_epoch',Integer,nullable=False),Column('created_at',Integer,nullable=False),
        Column('last_seen',Integer,nullable=False),Column('expires_at',Integer,nullable=False))
    Table('password_resets',m,Column('token_hash',Text,primary_key=True),Column('user_id',Integer,ForeignKey('users.id',ondelete='CASCADE'),nullable=False,index=True),
        Column('expires_at',Integer,nullable=False),Column('used',Boolean,nullable=False))
    Table('addresses',m,Column('id',Integer,primary_key=True),Column('user_id',Integer,ForeignKey('users.id',ondelete='CASCADE'),nullable=False,index=True),
        *[Column(name,Text,nullable=False) for name in ('label','full_name','line1','line2','city','region','postal_code','country')])
    Table('rate_limits',m,Column('key_hash',Text,primary_key=True),Column('window_start',Integer,nullable=False),Column('count',Integer,nullable=False))
    Table('audit_records',m,Column('id',Integer,primary_key=True),Column('actor_id',Integer,ForeignKey('users.id',ondelete='SET NULL')),
        Column('action',Text,nullable=False),Column('resource',Text,nullable=False),Column('resource_id',Text,nullable=False),Column('created_at',Integer,nullable=False))
    return m


def migrate_identity(engine,metadata):
    with engine.begin() as conn:
        if engine.dialect.name=='postgresql':conn.execute(text('SELECT pg_advisory_xact_lock(681072014)'))
        versions=dict(conn.execute(text('SELECT revision,checksum FROM projectforge_migrations')).all())
        if '0001' not in versions:raise RuntimeError('Catalogue migration 0001 must precede identity')
        if '0002' in versions:
            if versions['0002']!=MIGRATION_HASH:raise RuntimeError('Identity migration checksum mismatch')
            return
        if any(inspect(conn).has_table(table) for table in metadata.tables):raise RuntimeError('Unversioned identity tables; migration refused')
        if 'version' in {c['name'] for c in inspect(conn).get_columns('products')}:raise RuntimeError('Unversioned product version column')
        conn.execute(text('ALTER TABLE products ADD COLUMN version INTEGER NOT NULL DEFAULT 1'))
        metadata.create_all(conn)
        conn.execute(text('INSERT INTO projectforge_migrations (revision,checksum) VALUES (:r,:c)'),{'r':'0002','c':MIGRATION_HASH})


def audit(conn,metadata,action,actor=None,resource='',resource_id='',now=None):
    conn.execute(metadata.tables['audit_records'].insert().values(actor_id=actor,action=action,resource=resource,
        resource_id=str(resource_id),created_at=int(time.time() if now is None else now)))


def create_admin(engine,metadata,email,password,name='Administrator'):
    validated=Register(email=email,password=password,name=name)
    encoded=hash_password(validated.password.get_secret_value())
    try:
        with engine.begin() as conn:
            uid=conn.execute(metadata.tables['users'].insert().values(email=validated.email,name=validated.name,password_hash=encoded,
                role='admin',active=True,auth_epoch=1,created_at=int(time.time()))).inserted_primary_key[0]
            audit(conn,metadata,'admin_bootstrapped',uid,'user',uid)
            return uid
    except IntegrityError:raise ValueError('Email already exists; no account was promoted') from None


class SecurityEnvelope:
    """Bound request bytes before parsing and attach private-response headers."""
    def __init__(self,app,local_only=False):self.app,self.local_only=app,local_only
    async def __call__(self,scope,receive,send):
        if scope['type']!='http':return await self.app(scope,receive,send)
        if self.local_only:
            try:local=ipaddress.ip_address(scope.get('client',('',''))[0]).is_loopback
            except ValueError:local=False
            if not local:return await JSONResponse({'detail':'Local development is loopback-only'},status_code=403)(scope,receive,send)
        chunks=[];size=0
        while True:
            message=await receive()
            if message['type']=='http.disconnect':return
            piece=message.get('body',b'');size+=len(piece)
            if size>65536:return await JSONResponse({'detail':'Request body too large'},status_code=413)(scope,receive,send)
            chunks.append(piece)
            if not message.get('more_body',False):break
        delivered=False
        async def replay():
            nonlocal delivered
            if not delivered:
                delivered=True;return {'type':'http.request','body':b''.join(chunks),'more_body':False}
            return await receive()
        async def secure_send(message):
            if message['type']=='http.response.start':
                headers=list(message.get('headers',[]))
                headers.extend([(b'x-content-type-options',b'nosniff'),(b'referrer-policy',b'no-referrer')])
                if scope['path'].startswith(('/api/auth','/api/account','/api/admin','/api/cart','/api/orders')):
                    headers=[(k,v) for k,v in headers if k.lower()!=b'cache-control']
                    headers.append((b'cache-control',b'no-store'))
                message={**message,'headers':headers}
            await send(message)
        await self.app(scope,replay,secure_send)


def create_app(identity_path=None,catalogue_path=None,database_url=None,clock=None,mail_sink=None,migration_followups=None):
    path=Path(identity_path or Path(__file__).with_name('identity.json'))
    config=IdentityContract.model_validate_json(path.read_text(encoding='utf-8')).model_dump(mode='json')
    origin=config['public_origin'].rstrip('/')
    parsed=urlsplit(origin)
    local=bool(config['allow_local_http'])
    if parsed.scheme!='https' and not (local and parsed.scheme=='http' and parsed.hostname in ('127.0.0.1','localhost','::1')):
        raise RuntimeError('Identity requires HTTPS or explicitly configured loopback HTTP')
    if local and parsed.hostname not in ('127.0.0.1','localhost','::1'):raise RuntimeError('Development identity is loopback-only')
    if identity_path is None and json.loads((path.parent.parent/'migrations/0002.json').read_text())!=MIGRATION:
        raise RuntimeError('Identity migration manifest mismatch')
    app=catalogue_app(catalogue_path,database_url,migration_followups={'0002':MIGRATION_HASH,**(migration_followups or {})})
    engine=app.state.engine
    metadata=identity_metadata()
    app.state.identity_metadata=metadata;app.state.identity_enabled=True
    app.state.identity_currency=json.loads(Path(catalogue_path or Path(__file__).with_name('catalogue.json')).read_text(encoding='utf-8'))['currency']
    now=lambda:int((clock or time.time)())
    base_lifespan=app.router.lifespan_context
    @asynccontextmanager
    async def lifespan(application):
        async with base_lifespan(application):
            migrate_identity(engine,metadata)
            products=app.state.metadata.tables['products']
            if 'version' not in products.c:products.append_column(Column('version',Integer,nullable=False))
            yield
    app.router.lifespan_context=lifespan
    app.add_middleware(SecurityEnvelope,local_only=local)
    @app.exception_handler(RequestValidationError)
    async def invalid_request(_,exc):
        return JSONResponse({'detail':[{'loc':e['loc'],'msg':e['msg'],'type':e['type']} for e in exc.errors()]},status_code=422)
    users,sessions,resets,addresses,rates=(metadata.tables[t] for t in ('users','sessions','password_resets','addresses','rate_limits'))
    cookie='pf_session_dev' if local else '__Host-pf_session'
    dummy=hash_password('not a real account password')

    def limited(request,scope,identifier='',limit=8,window=900,*,per_ip=True,global_limit=200):
        current=now();bucket=current//window*window
        ip=request.client.host if request.client else 'unknown'
        keys=[(scope+'|account|'+identifier,limit)]
        if per_ip:keys.append((scope+'|ip|'+ip,40))
        if global_limit is not None:keys.append((scope+'|global',global_limit))
        counts=[]
        with engine.begin() as conn:
            conn.execute(delete(rates).where(rates.c.window_start<current-86400))
            for key,maximum in keys:
                value=digest(key+'|'+str(bucket))
                if engine.dialect.name=='postgresql':
                    from sqlalchemy.dialects.postgresql import insert as upsert
                else:
                    from sqlalchemy.dialects.sqlite import insert as upsert
                statement=upsert(rates).values(key_hash=value,window_start=bucket,count=1)
                count=conn.execute(statement.on_conflict_do_update(index_elements=[rates.c.key_hash],set_={'count':rates.c.count+1}).returning(rates.c.count)).scalar_one()
                counts.append((count,maximum))
        if any(count>maximum for count,maximum in counts):raise HTTPException(429,'Too many attempts. Try again later.',headers={'Retry-After':str(window-(current-bucket))})

    def put_cookie(response,token,lifetime):
        response.set_cookie(cookie,token,max_age=lifetime,httponly=True,secure=not local,samesite='lax',path='/')

    def clear_cookie(response):response.delete_cookie(cookie,httponly=True,secure=not local,samesite='lax',path='/')

    def new_session(conn,response,user=None):
        token,csrf=secrets.token_urlsafe(32),secrets.token_urlsafe(32)
        lifetime=config['session_absolute_seconds'] if user else 900
        current=now()
        conn.execute(delete(sessions).where(sessions.c.expires_at<=current))
        if user:
            existing=conn.execute(select(sessions.c.id_hash).where(sessions.c.user_id==user['id']).order_by(sessions.c.created_at.desc(),sessions.c.id_hash)).scalars().all()
            if len(existing)>=5:conn.execute(delete(sessions).where(sessions.c.id_hash.in_(existing[4:])))
        conn.execute(sessions.insert().values(id_hash=digest(token),user_id=user['id'] if user else None,csrf=csrf,
            auth_epoch=user['auth_epoch'] if user else 0,created_at=current,last_seen=current,expires_at=current+lifetime))
        put_cookie(response,token,lifetime)
        return csrf

    def session(request,authenticated=False):
        token=request.cookies.get(cookie,'')
        if len(token)!=43:raise HTTPException(401,'Sign in required')
        with engine.begin() as conn:
            row=conn.execute(select(sessions).where(sessions.c.id_hash==digest(token))).mappings().first()
            if not row or row['expires_at']<=now() or row['last_seen']+(config['session_idle_seconds'] if row['user_id'] else 900)<=now():
                raise HTTPException(401,'Session expired; sign in again')
            user=conn.execute(select(users).where(users.c.id==row['user_id'])).mappings().first() if row['user_id'] else None
            if row['user_id'] and (not user or not user['active'] or user['auth_epoch']!=row['auth_epoch']):raise HTTPException(401,'Session no longer valid')
            if authenticated and not user:raise HTTPException(401,'Sign in required')
            conn.execute(update(sessions).where(sessions.c.id_hash==row['id_hash']).values(last_seen=now()))
            return dict(row),dict(user) if user else None

    def csrf(request,authenticated=False,admin=False):
        if request.headers.get('origin')!=origin:raise HTTPException(403,'Request origin is not allowed')
        if request.headers.get('sec-fetch-site')=='cross-site':raise HTTPException(403,'Cross-site request rejected')
        row,user=session(request,authenticated)
        supplied=request.headers.get('x-csrf-token','')
        if len(supplied)!=43 or not hmac.compare_digest(supplied,row['csrf']):raise HTTPException(403,'CSRF token is missing or invalid')
        if admin and user['role']!='admin':
            with engine.begin() as conn:audit(conn,metadata,'authorization_denied',user['id'],'admin',now=now())
            raise HTTPException(403,'Administrator role required')
        return row,user

    def require_admin(request):
        _,user=session(request,True)
        if user['role']!='admin':raise HTTPException(403,'Administrator role required')
        return user

    def user_view(user):return {k:user[k] for k in ('id','email','name','role')}

    @app.get('/api/auth/csrf')
    def get_csrf(request:Request,response:Response):
        try:row,_=session(request);return {'csrf_token':row['csrf']}
        except HTTPException:
            limited(request,'anonymous-session',limit=100,window=900)
            with engine.begin() as conn:token=new_session(conn,response)
            return {'csrf_token':token}

    @app.post('/api/auth/register')
    def register(payload:Register,request:Request):
        csrf(request);limited(request,'register',payload.email,limit=5)
        encoded=hash_password(payload.password.get_secret_value())
        try:
            with engine.begin() as conn:
                uid=conn.execute(users.insert().values(email=payload.email,name=payload.name,password_hash=encoded,role='customer',active=True,auth_epoch=1,created_at=now())).inserted_primary_key[0]
                audit(conn,metadata,'account_registered',uid,'user',uid,now())
        except IntegrityError:pass
        return {'message':'Continue to sign in with your account.'}

    @app.post('/api/auth/login')
    def login(payload:Credentials,request:Request,response:Response):
        old,_=csrf(request);limited(request,'login',payload.email)
        with engine.connect() as conn:user=conn.execute(select(users).where(users.c.email==payload.email)).mappings().first()
        valid=verify_password(payload.password.get_secret_value(),user['password_hash'] if user else dummy)
        if not user or not valid or not user['active']:
            with engine.begin() as conn:audit(conn,metadata,'login_failed',resource='credential',resource_id=digest(payload.email),now=now())
            raise HTTPException(401,'Email or password is incorrect')
        with engine.begin() as conn:
            current=conn.execute(select(users).where(users.c.id==user['id']).with_for_update()).mappings().one()
            if current['password_hash']!=user['password_hash'] or not current['active']:raise HTTPException(401,'Email or password is incorrect')
            conn.execute(delete(sessions).where(sessions.c.id_hash==old['id_hash']))
            token=new_session(conn,response,current)
            audit(conn,metadata,'login_succeeded',current['id'],'user',current['id'],now())
        return {'user':user_view(current),'csrf_token':token}

    @app.get('/api/account')
    def account(request:Request):return user_view(session(request,True)[1])

    @app.patch('/api/account')
    def profile(payload:Profile,request:Request):
        _,user=csrf(request,True)
        with engine.begin() as conn:
            conn.execute(update(users).where(users.c.id==user['id']).values(name=payload.name))
            audit(conn,metadata,'profile_updated',user['id'],'user',user['id'],now())
        return {**user_view(user),'name':payload.name}

    @app.post('/api/auth/logout')
    def logout(request:Request,response:Response):
        row,user=csrf(request)
        with engine.begin() as conn:
            conn.execute(delete(sessions).where(sessions.c.id_hash==row['id_hash']))
            audit(conn,metadata,'logged_out',user['id'] if user else None,now=now())
        clear_cookie(response);return {'message':'Signed out'}

    def send_recovery(email,token):
        link=origin+'/account/reset#token='+token
        try:
            if mail_sink:mail_sink(email,link);return
            mode=os.environ.get('IDENTITY_MAIL_MODE','local-outbox' if local else 'disabled')
            if mode=='local-outbox' and local:
                directory=Path(os.environ.get('IDENTITY_OUTBOX_DIR',str(Path(tempfile.gettempdir())/('projectforge-mail-'+digest(origin)[:12]))))
                directory.mkdir(parents=True,exist_ok=True,mode=0o700)
                filename=directory/(secrets.token_hex(16)+'.json')
                descriptor=os.open(filename,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
                with os.fdopen(descriptor,'w',encoding='utf-8') as target:json.dump({'to':email,'recovery_url':link},target)
            elif mode=='smtp' and not local:
                message=EmailMessage();message['To']=email;message['From']=os.environ['IDENTITY_MAIL_FROM'];message['Subject']='Reset your password'
                message.set_content('Use this single-use link to reset your password:\n'+link)
                import ssl
                with smtplib.SMTP(os.environ['IDENTITY_SMTP_HOST'],int(os.environ.get('IDENTITY_SMTP_PORT','587')),timeout=10) as smtp:
                    smtp.starttls(context=ssl.create_default_context());smtp.login(os.environ['IDENTITY_SMTP_USER'],os.environ['IDENTITY_SMTP_PASSWORD']);smtp.send_message(message)
            else:raise RuntimeError('Recovery delivery not configured')
        except Exception:
            with engine.begin() as conn:audit(conn,metadata,'recovery_delivery_failed',resource='mail',now=now())

    @app.post('/api/auth/forgot-password')
    def forgot(payload:Forgot,request:Request,background:BackgroundTasks):
        csrf(request);limited(request,'recovery',payload.email,limit=5)
        token=secrets.token_urlsafe(32)
        with engine.begin() as conn:
            user=conn.execute(select(users).where(users.c.email==payload.email,users.c.active.is_(True))).mappings().first()
            if user:
                conn.execute(resets.insert().values(token_hash=digest(token),user_id=user['id'],expires_at=now()+config['recovery_seconds'],used=False))
                audit(conn,metadata,'recovery_requested',user['id'],'user',user['id'],now())
                background.add_task(send_recovery,payload.email,token)
        return {'message':'If an account exists, recovery instructions will be sent.'}

    @app.post('/api/auth/reset-password')
    def reset(payload:Reset,request:Request,response:Response):
        old,_=csrf(request)
        # Invalid tokens consume only the caller's persistent IP allowance.
        # A shared empty account/global bucket lets one visitor block all recovery.
        ip=request.client.host if request.client else 'unknown'
        limited(request,'reset-attempt',ip,limit=40,per_ip=False,global_limit=None)
        with engine.connect() as conn:record=conn.execute(select(resets).where(resets.c.token_hash==digest(payload.token))).mappings().first()
        if not record or record['used'] or record['expires_at']<=now():raise HTTPException(400,'Recovery link is invalid or expired')
        limited(request,'reset-user',str(record['user_id']),limit=8,per_ip=False,global_limit=None)
        encoded=hash_password(payload.password.get_secret_value())
        with engine.begin() as conn:
            # All credential changes lock the user before reset rows, avoiding
            # opposite lock order between recovery and password-change requests.
            user=conn.execute(select(users).where(users.c.id==record['user_id']).with_for_update()).mappings().one()
            record=conn.execute(select(resets).where(resets.c.token_hash==digest(payload.token)).with_for_update()).mappings().first()
            if not record or record['used'] or record['expires_at']<=now():raise HTTPException(400,'Recovery link is invalid or expired')
            conn.execute(update(users).where(users.c.id==user['id']).values(password_hash=encoded,auth_epoch=user['auth_epoch']+1))
            conn.execute(update(resets).where(resets.c.user_id==user['id']).values(used=True))
            conn.execute(delete(sessions).where((sessions.c.user_id==user['id'])|(sessions.c.id_hash==old['id_hash'])))
            audit(conn,metadata,'password_reset',user['id'],'user',user['id'],now())
        clear_cookie(response);return {'message':'Password reset. Sign in again.'}

    @app.post('/api/account/password')
    def change_password(payload:ChangePassword,request:Request,response:Response):
        _,user=csrf(request,True);limited(request,'password-change',str(user['id']),limit=5)
        if not verify_password(payload.current_password.get_secret_value(),user['password_hash']):raise HTTPException(401,'Current password is incorrect')
        encoded=hash_password(payload.password.get_secret_value())
        with engine.begin() as conn:
            current=conn.execute(select(users).where(users.c.id==user['id']).with_for_update()).mappings().one()
            if current['password_hash']!=user['password_hash']:raise HTTPException(409,'Account changed; sign in again')
            conn.execute(update(users).where(users.c.id==user['id']).values(password_hash=encoded,auth_epoch=current['auth_epoch']+1))
            conn.execute(delete(sessions).where(sessions.c.user_id==user['id']))
            conn.execute(update(resets).where(resets.c.user_id==user['id']).values(used=True))
            audit(conn,metadata,'password_changed',user['id'],'user',user['id'],now())
        clear_cookie(response);return {'message':'Password changed. Sign in again.'}

    @app.get('/api/account/addresses')
    def list_addresses(request:Request):
        _,user=session(request,True)
        with engine.connect() as conn:
            return [{k:v for k,v in row.items() if k!='user_id'} for row in conn.execute(select(addresses).where(addresses.c.user_id==user['id']).order_by(addresses.c.id)).mappings()]

    @app.post('/api/account/addresses',status_code=201)
    def add_address(payload:Address,request:Request):
        _,user=csrf(request,True)
        with engine.begin() as conn:
            conn.execute(select(users.c.id).where(users.c.id==user['id']).with_for_update()).one()
            count=conn.execute(select(addresses.c.id).where(addresses.c.user_id==user['id'])).all()
            if len(count)>=20:raise HTTPException(409,'Address limit reached')
            aid=conn.execute(addresses.insert().values(user_id=user['id'],**payload.model_dump())).inserted_primary_key[0]
            audit(conn,metadata,'address_created',user['id'],'address',aid,now())
        return {'id':aid,**payload.model_dump()}

    @app.put('/api/account/addresses/{address_id}')
    def edit_address(address_id:int,payload:Address,request:Request):
        _,user=csrf(request,True)
        with engine.begin() as conn:
            changed=conn.execute(update(addresses).where(addresses.c.id==address_id,addresses.c.user_id==user['id']).values(**payload.model_dump()))
            if not changed.rowcount:raise HTTPException(404,'Address not found')
            audit(conn,metadata,'address_updated',user['id'],'address',address_id,now())
        return {'id':address_id,**payload.model_dump()}

    @app.delete('/api/account/addresses/{address_id}',status_code=204)
    def remove_address(address_id:int,request:Request):
        _,user=csrf(request,True)
        with engine.begin() as conn:
            changed=conn.execute(delete(addresses).where(addresses.c.id==address_id,addresses.c.user_id==user['id']))
            if not changed.rowcount:raise HTTPException(404,'Address not found')
            audit(conn,metadata,'address_deleted',user['id'],'address',address_id,now())
        return Response(status_code=204)

    app.state.identity_session=session;app.state.identity_csrf=csrf;app.state.identity_admin=require_admin
    app.state.identity_limited=limited
    register_admin(app,engine,metadata,csrf,require_admin,now)
    return app


def register_admin(app,engine,metadata,csrf,require_admin,now):
    def commerce_guard(conn):
        if getattr(app.state,'order_enabled',False) and conn.dialect.name=='postgresql':
            conn.execute(text("SET LOCAL lock_timeout = '5s'"))
            conn.execute(text('SELECT pg_advisory_xact_lock(681072015)'))
    catalogue=app.state.metadata
    products,categories,variants,images=(catalogue.tables[t] for t in ('products','categories','variants','product_images'))

    def product_view(conn,row):
        category=conn.execute(select(categories.c.slug).where(categories.c.id==row['category_id'])).scalar_one()
        return {'id':row['id'],'version':row['version'],'product':{**{k:row[k] for k in ('slug','name','description','material','active')},'category_slug':category,
            'variants':[{k:v[k] for k in ('sku','label','options','price_minor','stock_quantity','active')} for v in conn.execute(select(variants).where(variants.c.product_id==row['id']).order_by(variants.c.id)).mappings()],
            'images':[{k:i[k] for k in ('asset','alt')} for i in conn.execute(select(images).where(images.c.product_id==row['id']).order_by(images.c.position)).mappings()]}}

    def save_product(conn,payload,product_id=None,expected=None):
        category_id=conn.execute(select(categories.c.id).where(categories.c.slug==payload.category_slug)).scalar_one_or_none()
        if category_id is None:raise HTTPException(422,'Choose an existing category')
        values={k:getattr(payload,k) for k in ('slug','name','description','material','active')};values['category_id']=category_id
        if product_id is None:
            pid=conn.execute(products.insert().values(**values,version=1)).inserted_primary_key[0]
        else:
            result=conn.execute(update(products).where(products.c.id==product_id,products.c.version==expected).values(**values,version=products.c.version+1))
            if not result.rowcount:raise HTTPException(409,'Product changed or is unavailable; reload before saving')
            pid=product_id
        existing={row['sku']:row for row in conn.execute(select(variants).where(variants.c.product_id==pid)).mappings()}
        conn.execute(update(variants).where(variants.c.product_id==pid).values(active=False))
        currency=conn.execute(select(variants.c.currency).limit(1)).scalar_one_or_none()
        if currency is None:
            # Currency comes from the fixed database CHECK/config, never a client field.
            currency=app.state.identity_currency
        for variant in payload.variants:
            data=variant.model_dump()
            if variant.sku in existing:conn.execute(update(variants).where(variants.c.id==existing[variant.sku]['id']).values(**data))
            else:conn.execute(variants.insert().values(product_id=pid,currency=currency,**data))
        conn.execute(delete(images).where(images.c.product_id==pid))
        for position,image in enumerate(payload.images):conn.execute(images.insert().values(product_id=pid,position=position,**image.model_dump()))
        return conn.execute(select(products).where(products.c.id==pid)).mappings().one()

    @app.get('/api/admin/products')
    def admin_products(request:Request):
        require_admin(request)
        with engine.connect() as conn:return [product_view(conn,row) for row in conn.execute(select(products).order_by(products.c.id).limit(200)).mappings()]

    @app.post('/api/admin/products',status_code=201)
    def create_product(payload:AdminProduct,request:Request):
        _,actor=csrf(request,True,True)
        try:
            with engine.begin() as conn:
                commerce_guard(conn)
                row=save_product(conn,payload)
                audit(conn,metadata,'product_created',actor['id'],'product',row['id'],now())
                return product_view(conn,row)
        except IntegrityError:raise HTTPException(409,'A slug, SKU or relationship conflicts with existing data') from None

    @app.put('/api/admin/products/{product_id}')
    def update_product(product_id:int,payload:ProductUpdate,request:Request):
        _,actor=csrf(request,True,True)
        try:
            with engine.begin() as conn:
                commerce_guard(conn)
                row=save_product(conn,payload.product,product_id,payload.expected_version)
                audit(conn,metadata,'product_updated',actor['id'],'product',product_id,now())
                return product_view(conn,row)
        except IntegrityError:raise HTTPException(409,'A slug, SKU or relationship conflicts with existing data') from None

    @app.delete('/api/admin/products/{product_id}',status_code=204)
    def archive_product(product_id:int,expected_version:int,request:Request):
        _,actor=csrf(request,True,True)
        with engine.begin() as conn:
            commerce_guard(conn)
            result=conn.execute(update(products).where(products.c.id==product_id,products.c.version==expected_version).values(active=False,version=products.c.version+1))
            if not result.rowcount:raise HTTPException(409,'Product changed or is unavailable; reload before archiving')
            audit(conn,metadata,'product_archived',actor['id'],'product',product_id,now())
        return Response(status_code=204)

    @app.put('/api/admin/variants/{sku}/stock')
    def stock(sku:str,payload:StockUpdate,request:Request):
        _,actor=csrf(request,True,True)
        with engine.begin() as conn:
            commerce_guard(conn)
            variant=conn.execute(select(variants).where(variants.c.sku==sku)).mappings().first()
            if not variant:raise HTTPException(404,'SKU not found')
            changed=conn.execute(update(products).where(products.c.id==variant['product_id'],products.c.version==payload.expected_version).values(version=products.c.version+1))
            if not changed.rowcount:raise HTTPException(409,'Product changed; reload before changing stock')
            conn.execute(update(variants).where(variants.c.id==variant['id']).values(stock_quantity=payload.quantity))
            audit(conn,metadata,'stock_updated',actor['id'],'sku',sku,now())
        return {'sku':sku,'quantity':payload.quantity,'version':payload.expected_version+1}

    @app.get('/api/admin/categories')
    def admin_categories(request:Request):
        require_admin(request)
        with engine.connect() as conn:return [dict(row) for row in conn.execute(select(categories).order_by(categories.c.id)).mappings()]

    @app.post('/api/admin/categories',status_code=201)
    def add_category(payload:CategoryInput,request:Request):
        _,actor=csrf(request,True,True)
        try:
            with engine.begin() as conn:
                commerce_guard(conn)
                cid=conn.execute(categories.insert().values(**payload.model_dump())).inserted_primary_key[0]
                audit(conn,metadata,'category_created',actor['id'],'category',cid,now())
                return {'id':cid,**payload.model_dump()}
        except IntegrityError:raise HTTPException(409,'Category slug already exists') from None

    @app.put('/api/admin/categories/{category_id}')
    def edit_category(category_id:int,payload:CategoryInput,request:Request):
        _,actor=csrf(request,True,True)
        try:
            with engine.begin() as conn:
                commerce_guard(conn)
                if not conn.execute(update(categories).where(categories.c.id==category_id).values(**payload.model_dump())).rowcount:raise HTTPException(404,'Category not found')
                audit(conn,metadata,'category_updated',actor['id'],'category',category_id,now())
                return {'id':category_id,**payload.model_dump()}
        except IntegrityError:raise HTTPException(409,'Category slug already exists') from None

    @app.get('/api/admin/audit')
    def audit_records(request:Request):
        require_admin(request)
        with engine.connect() as conn:return [dict(row) for row in conn.execute(select(metadata.tables['audit_records']).order_by(metadata.tables['audit_records'].c.id.desc()).limit(200)).mappings()]
