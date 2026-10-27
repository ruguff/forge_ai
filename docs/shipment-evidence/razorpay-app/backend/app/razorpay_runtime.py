"""Razorpay TEST adapter; callback/webhook payloads never authorize fulfillment."""
import json
import re
import uuid
from pathlib import Path
from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool
from pydantic import Field
from sqlalchemy import (MetaData, Table, Column, Integer, BigInteger, Text, Boolean,
                        ForeignKey, UniqueConstraint, CheckConstraint, select, update, text, inspect)
from .order_runtime import Input, checksum, lock, create_app as order_app
from .identity_runtime import audit
from .razorpay_client import RazorpayTestClient, ProviderUnavailable, ProviderMismatch, identifier
"""Non-secret test integration configuration. Live mode is not supported."""
from typing import Literal
StrictContract = Input


class RazorpayTestContract(StrictContract):
    version: Literal[1] = 1
    mode: Literal['razorpay_test'] = 'razorpay_test'
    currency: Literal['INR'] = 'INR'
    refunds: Literal['admin_full_only'] = 'admin_full_only'


SCHEMA = {'revision': '0004_razorpay_test', 'parent': '0003', 'module': 'razorpay-test-v1',
          'tables': ['razorpay_bindings', 'razorpay_refunds', 'razorpay_events'],
          'order_states': ['awaiting_payment', 'cancelled', 'expired', 'razorpay_test_paid', 'razorpay_test_refunded']}


class Key(Input):
    idempotency_key: str = Field(min_length=16, max_length=80, pattern=r'^[A-Za-z0-9_-]+$')


class Callback(Input):
    razorpay_order_id: str = Field(pattern=r'^order_[A-Za-z0-9]{1,80}$')
    razorpay_payment_id: str = Field(pattern=r'^pay_[A-Za-z0-9]{1,80}$')
    razorpay_signature: str = Field(pattern=r'^[0-9a-f]{64}$')


def metadata():
    m = MetaData()
    Table('orders', m, Column('id', Integer, primary_key=True))
    Table('users', m, Column('id', Integer, primary_key=True))
    Table('razorpay_bindings', m, Column('order_id', Integer, ForeignKey('orders.id'), primary_key=True),
          Column('receipt', Text, nullable=False, unique=True), Column('provider_order_id', Text, unique=True),
          Column('payment_id', Text, unique=True), Column('account_id', Text, nullable=False),
          Column('amount_minor', BigInteger, nullable=False), Column('currency', Text, nullable=False),
          Column('state', Text, nullable=False), Column('stock_consumed', Boolean, nullable=False),
          Column('created_at', BigInteger, nullable=False), Column('checked_at', BigInteger, nullable=False),
          CheckConstraint('amount_minor >= 100'), CheckConstraint("currency='INR'"),
          CheckConstraint("state IN ('creating','pending','authorized','failed','captured','late_capture','refunded','review')"))
    Table('razorpay_refunds', m, Column('id', Integer, primary_key=True),
          Column('order_id', Integer, ForeignKey('orders.id'), nullable=False),
          Column('actor_id', Integer, ForeignKey('users.id'), nullable=False),
          Column('request_key', Text, nullable=False), Column('provider_key', Text, nullable=False, unique=True),
          Column('provider_id', Text, unique=True), Column('payment_id', Text, nullable=False),
          Column('amount_minor', BigInteger, nullable=False), Column('state', Text, nullable=False),
          Column('created_at', BigInteger, nullable=False), UniqueConstraint('order_id', 'request_key'),
          CheckConstraint('amount_minor >= 100'), CheckConstraint("state IN ('creating','pending','processed','failed')"))
    Table('razorpay_events', m, Column('event_id', Text, primary_key=True), Column('body_hash', Text, nullable=False),
          Column('kind', Text, nullable=False), Column('created_at', BigInteger, nullable=False))
    return m


def create_app(provider_path=None, order_path=None, identity_path=None, catalogue_path=None,
               database_url=None, clock=None, mail_sink=None, client_factory=None):
    path = Path(provider_path or Path(__file__).with_name('razorpay.json'))
    config = RazorpayTestContract.model_validate_json(path.read_text(encoding='utf-8'))
    schema = {**SCHEMA, 'rules': config.model_dump(mode='json')}; digest = checksum(schema)
    if provider_path is None and json.loads((path.parent.parent/'migrations/0004_razorpay_test.json').read_text(encoding='utf-8')) != schema:
        raise RuntimeError('Razorpay test manifest mismatch')
    m = metadata(); bindings, refunds, events = (m.tables[k] for k in SCHEMA['tables'])

    def install(conn, application):
        if conn.dialect.name != 'postgresql': raise RuntimeError('Razorpay test module requires PostgreSQL')
        versions = dict(conn.execute(text('SELECT revision,checksum FROM projectforge_migrations')).all())
        if SCHEMA['revision'] in versions:
            if versions[SCHEMA['revision']] != digest: raise RuntimeError('Provider migration checksum mismatch')
            return
        if any(inspect(conn).has_table(k) for k in SCHEMA['tables']): raise RuntimeError('Unversioned provider tables')
        checks = [c for c in inspect(conn).get_check_constraints('orders') if 'awaiting_payment' in c['sqltext'] and 'expired' in c['sqltext']]
        if len(checks) != 1: raise RuntimeError('Ambiguous order state migration')
        conn.execute(text('ALTER TABLE orders DROP CONSTRAINT '+conn.dialect.identifier_preparer.quote(checks[0]['name'])))
        conn.execute(text("ALTER TABLE orders ADD CONSTRAINT order_state_rzp_test CHECK (state IN ('awaiting_payment','cancelled','expired','razorpay_test_paid','razorpay_test_refunded'))"))
        m.create_all(conn, tables=[bindings, refunds, events])
        conn.execute(text("CREATE UNIQUE INDEX one_active_rzp_refund ON razorpay_refunds(order_id) WHERE state IN ('creating','pending','processed')"))
        conn.execute(text('INSERT INTO projectforge_migrations (revision,checksum) VALUES (:r,:c)'), {'r': SCHEMA['revision'], 'c': digest})

    app = order_app(order_path, identity_path, catalogue_path, database_url, clock, mail_sink,
                    migration_followups={SCHEMA['revision']: digest}, install_extension=install)
    app.state.razorpay_test = True
    app.state.razorpay_client_factory = client_factory or RazorpayTestClient.from_environment
    engine = app.state.engine; now = app.state.order_now
    orders = app.state.order_metadata.tables['orders']; items = app.state.order_metadata.tables['order_items']
    variants = app.state.metadata.tables['variants']; products = app.state.metadata.tables['products']

    @app.exception_handler(ProviderUnavailable)
    async def unavailable(request, exc):
        return JSONResponse({'detail': 'Razorpay test service unavailable or unconfigured. Reconcile uncertain operations before retrying.'}, status_code=503)

    @app.exception_handler(ProviderMismatch)
    async def mismatch(request, exc):
        return JSONResponse({'detail': 'Provider evidence did not match the saved order. Administrator review required.'}, status_code=409)

    def client(): return app.state.razorpay_client_factory()

    def actor(request, administrative=False):
        _, user = app.state.identity_csrf(request, True)
        if administrative: app.state.identity_admin(request)
        app.state.identity_limited(request, 'rzp-'+request.scope['route'].name, str(user['id']), limit=20, window=300)
        return user

    def owned(conn, oid, user, administrative=False):
        row = conn.execute(select(orders).where(orders.c.id == oid)).mappings().first()
        if not row or (not administrative and row['user_id'] != user['id']): raise HTTPException(404, 'Order not found')
        return row

    def binding(conn, oid):
        row = conn.execute(select(bindings).where(bindings.c.order_id == oid)).mappings().first()
        if not row: raise HTTPException(404, 'No provider order has been started')
        return row

    def check_account(b, gateway):
        if b['account_id'] != gateway.account_id: raise ProviderMismatch('Provider account changed')

    def check_order(b, obj):
        if not isinstance(obj,dict):raise ProviderMismatch('Invalid provider order')
        identifier(obj.get('id'), 'order')
        if (obj.get('entity') != 'order' or obj.get('receipt') != b['receipt'] or type(obj.get('amount')) is not int
                or obj['amount'] != b['amount_minor'] or obj.get('currency') != b['currency']
                or b['provider_order_id'] and obj['id'] != b['provider_order_id']):
            raise ProviderMismatch('Provider order mismatch')

    def record(conn, action, oid, uid=None): audit(conn, app.state.identity_metadata, action, uid, 'razorpay_test', oid, now())

    def view(conn, row):
        b = conn.execute(select(bindings).where(bindings.c.order_id == row['id'])).mappings().first()
        return {'payment_mode': 'razorpay_test', 'payment_status': b['state'] if b else 'not_started',
                'provider_payment': {k: b[k] for k in ('provider_order_id', 'payment_id', 'state', 'checked_at')} if b else None,
                'provider_refunds': [{k:r[k] for k in ('id','provider_id','state')} for r in conn.execute(select(refunds).where(refunds.c.order_id == row['id']).order_by(refunds.c.id)).mappings()]}
    app.state.order_payment_view = view

    def result(oid):
        with engine.connect() as conn:
            row = conn.execute(select(orders).where(orders.c.id == oid)).mappings().one()
            return {'order_id': oid, 'order_state': row['state'], **view(conn,row)}

    def restore(conn, oid):
        for i in conn.execute(select(items).where(items.c.order_id == oid)).mappings():
            v = conn.execute(select(variants).where(variants.c.id == i['variant_id'])).mappings().one()
            conn.execute(update(variants).where(variants.c.id == v['id']).values(stock_quantity=variants.c.stock_quantity+i['quantity']))
            conn.execute(update(products).where(products.c.id == v['product_id']).values(version=products.c.version+1))

    def apply_payment(oid, payment, provider_order):
        if not isinstance(payment,dict):raise ProviderMismatch('Invalid provider payment')
        app.state.expire_reservations()
        with engine.begin() as conn:
            lock(conn); b = binding(conn, oid); check_order(b, provider_order)
            identifier(payment.get('id'), 'pay')
            if (payment.get('entity') != 'payment' or payment.get('order_id') != b['provider_order_id']
                    or type(payment.get('amount')) is not int or payment['amount'] != b['amount_minor']
                    or payment.get('currency') != b['currency']): raise ProviderMismatch('Payment mismatch')
            status = payment.get('status')
            if status not in ('created','authorized','captured','failed','refunded'): raise ProviderMismatch('Unknown payment status')
            returned=payment.get('amount_refunded',0)
            if type(returned) is not int or not 0<=returned<=b['amount_minor']:raise ProviderMismatch('Invalid refunded amount')
            if status in ('captured','refunded') and (payment.get('captured') is not True or provider_order.get('status') != 'paid'):
                raise ProviderMismatch('Capture not confirmed by provider order')
            row = conn.execute(select(orders).where(orders.c.id == oid)).mappings().one()
            if b['state'] in ('captured','late_capture','refunded','review'):
                if status in ('captured','refunded') and b['payment_id'] != payment['id']: raise ProviderMismatch('Multiple captured payments')
                known_refund=conn.execute(select(refunds.c.id).where(refunds.c.order_id==oid,refunds.c.state.in_(['creating','pending','processed']))).first()
                if payment.get('amount_refunded',0) and b['state']!='refunded' and not known_refund:
                    conn.execute(update(bindings).where(bindings.c.order_id==oid).values(state='review',checked_at=now()))
                    record(conn,'rzp_test_external_refund_review',oid)
                return # Never regress to an older notification or failed attempt.
            values = {'checked_at': now()}
            if status in ('captured','refunded'):
                active = row['state'] == 'awaiting_payment' and row['expires_at'] > now()
                values.update(payment_id=payment['id'], state='captured' if active else 'late_capture', stock_consumed=active)
                if active: conn.execute(update(orders).where(orders.c.id == oid).values(state='razorpay_test_paid'))
                # External refunds require reconciliation/operator review, never silent restocking.
                if payment.get('amount_refunded',0): values['state'] = 'review'
            elif status == 'authorized': values['state'] = 'authorized'
            elif status == 'failed' and b['state'] != 'authorized': values['state'] = 'failed'
            conn.execute(update(bindings).where(bindings.c.order_id == oid).values(**values))
            record(conn,'rzp_test_'+values.get('state',b['state']),oid)

    def attach(oid, obj, gateway):
        with engine.begin() as conn:
            lock(conn); b = binding(conn,oid); check_account(b,gateway); check_order(b,obj)
            conn.execute(update(bindings).where(bindings.c.order_id == oid).values(provider_order_id=obj['id'],state='pending' if b['state']=='creating' else b['state'],checked_at=now()))

    def reconcile(oid, gateway):
        with engine.connect() as conn: b = dict(binding(conn,oid))
        check_account(b,gateway)
        obj = gateway.order(b['provider_order_id']) if b['provider_order_id'] else gateway.find_order(b['receipt'])
        if obj is None: raise ProviderUnavailable('Provider creation still uncertain; do not recreate')
        attach(oid,obj,gateway)
        found = gateway.payments(obj['id'])
        # Prefer captured evidence over failed/authorized attempts. Each candidate
        # is fetched again from the provider API before it can change local state.
        priority={'created':0,'failed':1,'authorized':2,'captured':3,'refunded':4}
        for candidate in sorted(found,key=lambda p:priority.get(p.get('status'),-1)):
            payment=gateway.payment(identifier(candidate.get('id'),'pay'))
            apply_payment(oid,payment,obj)
        with engine.connect() as conn:
            known=[dict(r) for r in conn.execute(select(refunds).where(refunds.c.order_id==oid,refunds.c.provider_id.is_not(None))).mappings()]
        for r in known: apply_refund(r['id'],gateway.fetch_refund(r['provider_id']))
        return result(oid)
    app.state.reconcile_razorpay_order = lambda oid: reconcile(oid,client())

    @app.post('/api/razorpay/orders/{order_id}/checkout')
    def checkout(order_id:int, request:Request):
        user=actor(request);gateway=client();app.state.expire_reservations();created=False
        with engine.begin() as conn:
            lock(conn);row=owned(conn,order_id,user)
            if row['state']!='awaiting_payment' or row['expires_at']<=now(): raise HTTPException(409,'Order is not payable')
            if row['currency']!='INR' or row['total_minor']<100: raise HTTPException(409,'Test adapter supports INR orders of at least 100 paise')
            b=conn.execute(select(bindings).where(bindings.c.order_id==order_id)).mappings().first()
            if not b:
                conn.execute(bindings.insert().values(order_id=order_id,receipt='pf_'+uuid.uuid4().hex,account_id=gateway.account_id,
                    amount_minor=row['total_minor'],currency=row['currency'],state='creating',stock_consumed=False,created_at=now(),checked_at=0))
                b=binding(conn,order_id);created=True;record(conn,'rzp_test_intent',order_id,user['id'])
            b=dict(b);check_account(b,gateway)
        # The durable intent precedes the network call; a crash/timeout never
        # grants permission to blindly submit a second create request.
        if created: attach(order_id,gateway.create_order(b['amount_minor'],b['currency'],b['receipt']),gateway)
        elif not b['provider_order_id']: reconcile(order_id,gateway)
        with engine.connect() as conn:
            b=binding(conn,order_id)
            row=owned(conn,order_id,user)
            if row['state']!='awaiting_payment' or row['expires_at']<=now():raise HTTPException(409,'Order is no longer payable; reconcile provider state')
            return {'mode':'razorpay_test','key':gateway.key_id,'order_id':b['provider_order_id'],'amount':b['amount_minor'],'currency':b['currency'],'name':'ProjectForge test store'}

    @app.post('/api/razorpay/orders/{order_id}/verify')
    def verify(order_id:int, payload:Callback, request:Request):
        user=actor(request);gateway=client()
        with engine.connect() as conn:
            owned(conn,order_id,user);b=dict(binding(conn,order_id))
        check_account(b,gateway)
        if payload.razorpay_order_id!=b['provider_order_id'] or not gateway.verify_checkout(b['provider_order_id'],payload.razorpay_payment_id,payload.razorpay_signature):
            raise HTTPException(400,'Invalid checkout signature')
        apply_payment(order_id,gateway.payment(payload.razorpay_payment_id),gateway.order(b['provider_order_id']))
        return result(order_id)

    @app.post('/api/razorpay/orders/{order_id}/reconcile')
    def customer_reconcile(order_id:int,request:Request):
        user=actor(request)
        with engine.connect() as conn:owned(conn,order_id,user)
        return reconcile(order_id,client())

    @app.post('/api/admin/razorpay/orders/{order_id}/reconcile')
    def admin_reconcile(order_id:int,request:Request):
        user=actor(request,True)
        with engine.connect() as conn:owned(conn,order_id,user,True)
        return reconcile(order_id,client())

    def apply_refund(rid, obj):
        if not isinstance(obj,dict):raise ProviderMismatch('Invalid provider refund')
        identifier(obj.get('id'),'rfnd')
        with engine.begin() as conn:
            lock(conn);r=conn.execute(select(refunds).where(refunds.c.id==rid)).mappings().one();b=binding(conn,r['order_id'])
            if (obj.get('entity')!='refund' or obj.get('payment_id')!=r['payment_id'] or type(obj.get('amount')) is not int
                or obj['amount']!=r['amount_minor'] or obj.get('currency')!=b['currency']
                or r['provider_id'] and obj['id']!=r['provider_id'] or obj.get('status') not in ('pending','processed','failed')):
                raise ProviderMismatch('Refund mismatch')
            if r['state']=='processed':return
            if r['state']=='failed' and obj['status']!='failed': raise ProviderMismatch('Terminal refund contradiction')
            if obj['status']=='processed':
                if b['stock_consumed'] and app.state.fulfillment_status(conn,r['order_id'])=='not_packed':restore(conn,r['order_id'])
                conn.execute(update(bindings).where(bindings.c.order_id==r['order_id']).values(state='refunded',stock_consumed=False,checked_at=now()))
                conn.execute(update(orders).where(orders.c.id==r['order_id']).values(state='razorpay_test_refunded'))
            conn.execute(update(refunds).where(refunds.c.id==rid).values(provider_id=obj['id'],state=obj['status']))
            record(conn,'rzp_test_refund_'+obj['status'],r['order_id'],r['actor_id'])

    @app.post('/api/admin/razorpay/orders/{order_id}/refund')
    def refund(order_id:int,payload:Key,request:Request):
        user=actor(request,True);gateway=client()
        return submit_refund(order_id,payload.idempotency_key,user,gateway)

    @app.post('/api/admin/razorpay/orders/{order_id}/retry-refund')
    def retry_refund(order_id:int,request:Request):
        user=actor(request,True);gateway=client()
        with engine.connect() as conn:
            owned(conn,order_id,user,True)
            r=conn.execute(select(refunds).where(refunds.c.order_id==order_id,refunds.c.state=='creating')).mappings().first()
            if not r:raise HTTPException(409,'No uncertain refund request to recover')
            request_key=r['request_key']
        return submit_refund(order_id,request_key,user,gateway)

    def submit_refund(order_id,request_key,user,gateway):
        # Refresh before authorizing a refund; failed upstream reads cannot
        # permit a new financial operation.
        reconcile(order_id,gateway)
        with engine.begin() as conn:
            lock(conn);owned(conn,order_id,user,True);b=binding(conn,order_id);check_account(b,gateway)
            r=conn.execute(select(refunds).where(refunds.c.order_id==order_id,refunds.c.request_key==request_key)).mappings().first()
            if not r:
                app.state.fulfillment_block_refund(conn,order_id)
                if b['state'] not in ('captured','late_capture'):raise HTTPException(409,'Payment is not eligible for a full test refund')
                if conn.execute(select(refunds.c.id).where(refunds.c.order_id==order_id,refunds.c.state.in_(['creating','pending','processed']))).first():raise HTTPException(409,'Existing refund must be reconciled')
                rid=conn.execute(refunds.insert().values(order_id=order_id,actor_id=user['id'],request_key=request_key,provider_key=uuid.uuid4().hex,
                    payment_id=b['payment_id'],amount_minor=b['amount_minor'],state='creating',created_at=now())).inserted_primary_key[0]
                r=conn.execute(select(refunds).where(refunds.c.id==rid)).mappings().one()
                record(conn,'rzp_test_refund_intent',order_id,user['id'])
            r=dict(r)
        if r['state']=='creating':apply_refund(r['id'],gateway.refund(r['payment_id'],r['amount_minor'],r['provider_key']))
        elif r['provider_id']:apply_refund(r['id'],gateway.fetch_refund(r['provider_id']))
        return result(order_id)

    def process_webhook(raw, signature, event_id):
        gateway=client()
        if not gateway.verify_webhook(raw,signature):raise HTTPException(400,'Invalid webhook signature')
        try:data=json.loads(raw)
        except ValueError:raise HTTPException(400,'Invalid webhook JSON')
        if not isinstance(data,dict) or data.get('account_id')!=gateway.account_id:raise HTTPException(400,'Webhook account mismatch')
        kind=data.get('event');body_hash=checksum(raw.hex())
        with engine.connect() as conn:
            old=conn.execute(select(events).where(events.c.event_id==event_id)).mappings().first()
        if old:
            if old['body_hash']!=body_hash:raise HTTPException(409,'Webhook ID reused with different content')
            return {'received':True,'duplicate':True}
        supported={'payment.authorized','payment.captured','payment.failed','order.paid','refund.created','refund.processed','refund.failed'}
        if kind not in supported:return {'received':True,'ignored':True}
        try:
            entity=data['payload'][kind.split('.')[0]]['entity']
            if kind.startswith('refund.'):
                provider_id=identifier(entity['id'],'rfnd')
                with engine.connect() as conn:r=conn.execute(select(refunds).where(refunds.c.provider_id==provider_id)).mappings().first()
                # A notification can beat the create response. Ask for redelivery;
                # unknown refund IDs never cause a financial state change.
                if not r:raise ProviderUnavailable('Refund notification arrived before binding')
                with engine.connect() as conn:check_account(binding(conn,r['order_id']),gateway)
                obj=gateway.fetch_refund(provider_id);apply_refund(r['id'],obj)
            else:
                oid=identifier(entity['id'] if kind=='order.paid' else entity['order_id'],'order')
                with engine.connect() as conn:b=conn.execute(select(bindings).where(bindings.c.provider_order_id==oid)).mappings().first()
                if not b:raise ProviderUnavailable('Order notification arrived before binding')
                reconcile(b['order_id'],gateway)
        except (KeyError,TypeError):raise HTTPException(400,'Malformed webhook entity') from None
        with engine.begin() as conn:
            lock(conn);old=conn.execute(select(events).where(events.c.event_id==event_id)).mappings().first()
            if old and old['body_hash']!=body_hash:raise HTTPException(409,'Webhook ID conflict')
            if not old:conn.execute(events.insert().values(event_id=event_id,body_hash=body_hash,kind=kind,created_at=now()))
        return {'received':True}

    @app.post('/api/razorpay/webhook')
    async def webhook(request:Request):
        raw=b''
        async for chunk in request.stream():
            raw+=chunk
            if len(raw)>65536:raise HTTPException(413,'Webhook body too large')
        event_id=request.headers.get('x-razorpay-event-id','')
        if not re.fullmatch(r'[A-Za-z0-9_-]{1,128}',event_id):raise HTTPException(400,'Webhook event ID required')
        return await run_in_threadpool(process_webhook,raw,request.headers.get('x-razorpay-signature',''),event_id)
    return app
