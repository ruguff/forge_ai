"""Reviewed unpaid-order lifecycle. No payment or fulfillment success is implied."""
import asyncio,contextlib,hashlib,json,time
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import Request,HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel,ConfigDict,Field,StrictInt
from sqlalchemy import MetaData,Table,Column,Integer,BigInteger,Text,ForeignKey,CheckConstraint,UniqueConstraint,JSON,select,update,delete,text,inspect
from sqlalchemy.exc import OperationalError
from .identity_runtime import create_app as identity_app,audit


SCHEMA={'revision':'0003','parent':'0002','module':'orders-v1','tables':['carts','cart_items','orders','order_items'],
        'states':['awaiting_payment','cancelled','expired'],'stock':'available units; subtract on reservation, restore once on release'}

class Input(BaseModel):model_config=ConfigDict(extra='forbid')
"""Explicit single-store rules. These are business configuration, not tax advice."""
from typing import Literal
from pydantic import Field,StrictInt
StrictContract=Input
class OrderContract(StrictContract):
    version:Literal[1]=1
    tax_basis_points:StrictInt=Field(ge=0,le=10000)
    shipping_minor:StrictInt=Field(ge=0,le=1000000)
    discount_basis_points:StrictInt=Field(ge=0,le=10000)
    reservation_seconds:StrictInt=Field(default=900,ge=60,le=3600)
    policy_label:str=Field(min_length=1,max_length=160)

class CartLine(Input):
    quantity:StrictInt=Field(ge=0,le=99)
    expected_version:StrictInt=Field(ge=0)
class Checkout(Input):
    address_id:StrictInt=Field(ge=1)
    cart_version:StrictInt=Field(ge=1)
    quote_hash:str=Field(pattern=r'^[0-9a-f]{64}$')
    idempotency_key:str=Field(min_length=16,max_length=80,pattern=r'^[A-Za-z0-9_-]+$')

def checksum(value):return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()

def lock(conn):
    if conn.dialect.name=='postgresql':
        conn.execute(text("SET LOCAL lock_timeout = '5s'"))
        conn.execute(text('SELECT pg_advisory_xact_lock(681072015)'))
    else:conn.execute(text('BEGIN IMMEDIATE'))

def order_metadata(currency):
    m=MetaData()
    Table('users',m,Column('id',Integer,primary_key=True))
    Table('variants',m,Column('id',Integer,primary_key=True))
    Table('carts',m,Column('user_id',Integer,ForeignKey('users.id'),primary_key=True),Column('version',Integer,nullable=False),CheckConstraint('version >= 0'))
    Table('cart_items',m,Column('user_id',Integer,ForeignKey('carts.user_id'),primary_key=True),Column('variant_id',Integer,ForeignKey('variants.id'),primary_key=True),
        Column('quantity',Integer,nullable=False),CheckConstraint('quantity BETWEEN 1 AND 99'))
    Table('orders',m,Column('id',Integer,primary_key=True),Column('user_id',Integer,ForeignKey('users.id'),nullable=False,index=True),
        Column('idempotency_key',Text,nullable=False),Column('request_hash',Text,nullable=False),Column('state',Text,nullable=False),
        Column('address_snapshot',JSON,nullable=False),Column('currency',Text,nullable=False),
        *[Column(k,BigInteger,nullable=False) for k in ('subtotal_minor','discount_minor','tax_minor','shipping_minor','total_minor')],
        Column('policy_snapshot',JSON,nullable=False),Column('created_at',BigInteger,nullable=False),Column('expires_at',BigInteger,nullable=False),
        UniqueConstraint('user_id','idempotency_key'),CheckConstraint("state IN ('awaiting_payment','cancelled','expired')"),
        CheckConstraint('subtotal_minor >= 0 AND discount_minor >= 0 AND discount_minor <= subtotal_minor AND tax_minor >= 0 AND shipping_minor >= 0 AND total_minor >= 0'),
        CheckConstraint('total_minor = subtotal_minor - discount_minor + tax_minor + shipping_minor'),CheckConstraint("currency = '"+currency+"'"))
    Table('order_items',m,Column('id',Integer,primary_key=True),Column('order_id',Integer,ForeignKey('orders.id'),nullable=False,index=True),
        Column('variant_id',Integer,ForeignKey('variants.id'),nullable=False),Column('product_name',Text,nullable=False),Column('sku',Text,nullable=False),Column('label',Text,nullable=False),
        Column('unit_price_minor',BigInteger,nullable=False),Column('quantity',Integer,nullable=False),Column('line_total_minor',BigInteger,nullable=False),
        UniqueConstraint('order_id','variant_id'),CheckConstraint('quantity BETWEEN 1 AND 99 AND unit_price_minor >= 0 AND line_total_minor = unit_price_minor * quantity'))
    return m

def create_app(order_path=None,identity_path=None,catalogue_path=None,database_url=None,clock=None,mail_sink=None,migration_followups=None,install_extension=None):
    path=Path(order_path or Path(__file__).with_name('orders.json'))
    config=OrderContract.model_validate_json(path.read_text(encoding='utf-8')).model_dump(mode='json')
    schema={**SCHEMA,'rules':config};migration_hash=checksum(schema)
    if order_path is None and json.loads((path.parent.parent/'migrations/0003.json').read_text(encoding='utf-8'))!=schema:raise RuntimeError('Order migration manifest mismatch')
    delivery_enabled=install_extension is not None
    if delivery_enabled:
        from .fulfillment_runtime import SCHEMA as DELIVERY_SCHEMA, configure
        migration_followups={**(migration_followups or {}), DELIVERY_SCHEMA['revision']: checksum(DELIVERY_SCHEMA)}
    app=identity_app(identity_path,catalogue_path,database_url,clock,mail_sink,migration_followups={'0003':migration_hash,**(migration_followups or {})})
    engine=app.state.engine;currency=app.state.identity_currency;m=order_metadata(currency)
    carts,lines,orders,items=(m.tables[k] for k in SCHEMA['tables'])
    users=app.state.identity_metadata.tables['users'];addresses=app.state.identity_metadata.tables['addresses']
    variants=app.state.metadata.tables['variants'];products=app.state.metadata.tables['products'];categories=app.state.metadata.tables['categories']
    now=lambda:int((clock or time.time)())
    app.state.order_enabled=True;app.state.order_metadata=m
    session=app.state.identity_session;csrf=app.state.identity_csrf;admin=app.state.identity_admin
    def record(conn,action,user=None,oid=''):
        audit(conn,app.state.identity_metadata,action,user,'order',oid,now())
    def release(conn,row,state):
        if row['state']!='awaiting_payment':return
        changed=conn.execute(update(orders).where(orders.c.id==row['id'],orders.c.state=='awaiting_payment').values(state=state))
        if not changed.rowcount:return
        for item in conn.execute(select(items).where(items.c.order_id==row['id']).order_by(items.c.variant_id)).mappings():
            variant=conn.execute(select(variants).where(variants.c.id==item['variant_id'])).mappings().one()
            conn.execute(update(variants).where(variants.c.id==variant['id']).values(stock_quantity=variants.c.stock_quantity+item['quantity']))
            conn.execute(update(products).where(products.c.id==variant['product_id']).values(version=products.c.version+1))
        record(conn,'order_'+state,None,row['id'])
        if hasattr(app.state,'order_released'):app.state.order_released(conn,row,state)
    def expire(conn):
        for row in conn.execute(select(orders).where(orders.c.state=='awaiting_payment',orders.c.expires_at<=now()).order_by(orders.c.id)).mappings().all():release(conn,row,'expired')
    def sweep():
        with engine.begin() as conn:lock(conn);expire(conn)
    app.state.expire_reservations=sweep
    app.state.order_expire=expire
    app.state.order_now=now
    install_delivery=configure(app) if delivery_enabled else None
    base=app.router.lifespan_context
    @asynccontextmanager
    async def lifespan(application):
        async with base(application):
            with engine.begin() as conn:
                if conn.dialect.name=='postgresql':conn.execute(text('SELECT pg_advisory_xact_lock(681072014)'))
                revisions=dict(conn.execute(text('SELECT revision,checksum FROM projectforge_migrations')).all())
                if '0002' not in revisions:raise RuntimeError('Identity migration required')
                if '0003' not in revisions:
                    if any(inspect(conn).has_table(k) for k in SCHEMA['tables']):raise RuntimeError('Unversioned order tables; migration refused')
                    m.create_all(conn,tables=[m.tables[k] for k in SCHEMA['tables']])
                    conn.execute(text('INSERT INTO projectforge_migrations (revision,checksum) VALUES (:r,:c)'),{'r':'0003','c':migration_hash})
                if install_extension:install_extension(conn,app)
                if install_delivery:install_delivery(conn)
            sweep()
            async def worker():
                while True:
                    await asyncio.sleep(30)
                    try:await asyncio.to_thread(sweep)
                    except OperationalError:pass # bounded lock contention; next sweep retries
            task=asyncio.create_task(worker())
            try:yield
            finally:
                task.cancel()
                with contextlib.suppress(asyncio.CancelledError):await task
    app.router.lifespan_context=lifespan
    @app.exception_handler(OperationalError)
    async def unavailable(_,exc):return JSONResponse({'detail':'Store is busy. Retry using the same order key.'},status_code=503)
    def cart(conn,uid):
        row=conn.execute(select(carts).where(carts.c.user_id==uid)).mappings().first()
        if not row:conn.execute(carts.insert().values(user_id=uid,version=0));return {'user_id':uid,'version':0}
        return row
    def quote(conn,uid):
        current=cart(conn,uid);result=[];subtotal=0
        query=select(lines.c.quantity,variants,products.c.name.label('product_name'),products.c.active.label('product_active'),categories.c.active.label('category_active')).join(variants,lines.c.variant_id==variants.c.id).join(products,variants.c.product_id==products.c.id).join(categories,products.c.category_id==categories.c.id).where(lines.c.user_id==uid).order_by(variants.c.id)
        for row in conn.execute(query).mappings():
            available=row['active'] and row['product_active'] and row['category_active'] and row['stock_quantity']>=row['quantity']
            amount=row['price_minor']*row['quantity'];subtotal+=amount
            result.append({'variant_id':row['id'],'sku':row['sku'],'product_name':row['product_name'],'label':row['label'],'quantity':row['quantity'],'unit_price_minor':row['price_minor'],'line_total_minor':amount,'available':bool(available)})
        discount=subtotal*config['discount_basis_points']//10000
        tax=((subtotal-discount)*config['tax_basis_points']+5000)//10000
        shipping=config['shipping_minor'] if result else 0
        response={'version':current['version'],'items':result,'currency':currency,'subtotal_minor':subtotal,'discount_minor':discount,'tax_minor':tax,'shipping_minor':shipping,'total_minor':subtotal-discount+tax+shipping,'policy':config,'can_checkout':bool(result) and all(i['available'] for i in result)}
        response['quote_hash']=checksum(response)
        return response
    def order_view(conn,row):
        payment=app.state.order_payment_view(conn,row) if hasattr(app.state,'order_payment_view') else {'payment_status':'not_implemented'}
        delivery={'fulfillment':app.state.fulfillment_view(conn,row)} if delivery_enabled else {}
        return {**delivery,**{k:v for k,v in row.items() if k not in ('idempotency_key','request_hash')},**payment,'items':[dict(i) for i in conn.execute(select(items).where(items.c.order_id==row['id']).order_by(items.c.id)).mappings()]}
    @app.get('/api/cart')
    def get_cart(request:Request):
        _,user=session(request,True)
        with engine.begin() as conn:lock(conn);expire(conn);return quote(conn,user['id'])
    @app.put('/api/cart/items/{sku}')
    def set_line(sku:str,payload:CartLine,request:Request):
        _,user=csrf(request,True)
        with engine.begin() as conn:
            lock(conn);expire(conn);current=cart(conn,user['id'])
            if current['version']!=payload.expected_version:raise HTTPException(409,'Cart changed. Reload before editing.')
            variant=conn.execute(select(variants).where(variants.c.sku==sku)).mappings().first()
            if not variant:raise HTTPException(404,'SKU not found')
            if payload.quantity:
                product=conn.execute(select(products).where(products.c.id==variant['product_id'])).mappings().one()
                active=conn.execute(select(categories.c.active).where(categories.c.id==product['category_id'])).scalar_one()
                if not active or not product['active'] or not variant['active']:raise HTTPException(409,'Product is unavailable')
                if variant['stock_quantity']<payload.quantity:raise HTTPException(409,'Insufficient available stock')
                existing=conn.execute(select(lines.c.variant_id).where(lines.c.user_id==user['id'])).scalars().all()
                if variant['id'] not in existing and len(existing)>=20:raise HTTPException(409,'Cart is limited to 20 SKUs')
            conn.execute(delete(lines).where(lines.c.user_id==user['id'],lines.c.variant_id==variant['id']))
            if payload.quantity:conn.execute(lines.insert().values(user_id=user['id'],variant_id=variant['id'],quantity=payload.quantity))
            conn.execute(update(carts).where(carts.c.user_id==user['id']).values(version=carts.c.version+1))
            return quote(conn,user['id'])
    @app.post('/api/orders',status_code=201)
    def checkout(payload:Checkout,request:Request):
        _,user=csrf(request,True)
        fingerprint=checksum(payload.model_dump(exclude={'idempotency_key'}))
        with engine.begin() as conn:
            lock(conn);expire(conn)
            old=conn.execute(select(orders).where(orders.c.user_id==user['id'],orders.c.idempotency_key==payload.idempotency_key)).mappings().first()
            if old:
                if old['request_hash']!=fingerprint:raise HTTPException(409,'Order key was already used for a different request')
                return order_view(conn,old)
            pending=conn.execute(select(orders.c.id).where(orders.c.user_id==user['id'],orders.c.state=='awaiting_payment').limit(5)).all()
            if len(pending)>=5:raise HTTPException(409,'Cancel or wait for existing reservations before ordering again')
            value=quote(conn,user['id'])
            if value['version']!=payload.cart_version or value['quote_hash']!=payload.quote_hash:raise HTTPException(409,'Cart or prices changed. Review a fresh quote.')
            if not value['can_checkout']:raise HTTPException(409,'Cart is empty or stock is unavailable')
            address=conn.execute(select(addresses).where(addresses.c.id==payload.address_id,addresses.c.user_id==user['id']).with_for_update()).mappings().first()
            if not address:raise HTTPException(404,'Owned address not found')
            oid=conn.execute(orders.insert().values(user_id=user['id'],idempotency_key=payload.idempotency_key,request_hash=fingerprint,state='awaiting_payment',
                address_snapshot={k:v for k,v in address.items() if k not in ('id','user_id')},currency=currency,policy_snapshot=config,created_at=now(),expires_at=now()+config['reservation_seconds'],
                **{k:value[k] for k in ('subtotal_minor','discount_minor','tax_minor','shipping_minor','total_minor')})).inserted_primary_key[0]
            for item in value['items']:
                variant=conn.execute(select(variants).where(variants.c.id==item['variant_id'])).mappings().one()
                changed=conn.execute(update(variants).where(variants.c.id==item['variant_id'],variants.c.stock_quantity>=item['quantity']).values(stock_quantity=variants.c.stock_quantity-item['quantity']))
                if not changed.rowcount:raise HTTPException(409,'Stock changed. Review your cart.')
                conn.execute(update(products).where(products.c.id==variant['product_id']).values(version=products.c.version+1))
                conn.execute(items.insert().values(order_id=oid,**{k:v for k,v in item.items() if k!='available'}))
            conn.execute(delete(lines).where(lines.c.user_id==user['id']))
            conn.execute(update(carts).where(carts.c.user_id==user['id']).values(version=carts.c.version+1))
            record(conn,'order_reserved',user['id'],oid)
            return order_view(conn,conn.execute(select(orders).where(orders.c.id==oid)).mappings().one())
    @app.get('/api/orders')
    def history(request:Request):
        _,user=session(request,True)
        with engine.begin() as conn:
            lock(conn);expire(conn)
            return [order_view(conn,row) for row in conn.execute(select(orders).where(orders.c.user_id==user['id']).order_by(orders.c.id.desc()).limit(100)).mappings()]
    @app.get('/api/orders/{order_id}')
    def detail(order_id:int,request:Request):
        _,user=session(request,True)
        with engine.begin() as conn:
            lock(conn);expire(conn)
            row=conn.execute(select(orders).where(orders.c.id==order_id,orders.c.user_id==user['id'])).mappings().first()
            if not row:raise HTTPException(404,'Order not found')
            return order_view(conn,row)
    @app.post('/api/orders/{order_id}/cancel')
    def cancel(order_id:int,request:Request):
        _,user=csrf(request,True)
        with engine.begin() as conn:
            lock(conn);expire(conn)
            row=conn.execute(select(orders).where(orders.c.id==order_id,orders.c.user_id==user['id'])).mappings().first()
            if not row:raise HTTPException(404,'Order not found')
            if row['state']=='expired':raise HTTPException(409,'Reservation expired')
            if row['state'] not in ('awaiting_payment','cancelled'):raise HTTPException(409,'Settled orders require an authorized refund')
            release(conn,row,'cancelled')
            return order_view(conn,conn.execute(select(orders).where(orders.c.id==order_id)).mappings().one())
    @app.get('/api/admin/orders')
    def admin_orders(request:Request):
        admin(request)
        with engine.begin() as conn:
            lock(conn);expire(conn)
            return [order_view(conn,row) for row in conn.execute(select(orders).order_by(orders.c.id.desc()).limit(100)).mappings()]
    return app
