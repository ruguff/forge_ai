"""Offline simulator only. No gateway, card input, credentials or real money."""
import json
from pathlib import Path
from typing import Literal
from fastapi import HTTPException, Request
from pydantic import Field, StrictInt
from sqlalchemy import (MetaData, Table, Column, Integer, BigInteger, Text,
                        ForeignKey, CheckConstraint, UniqueConstraint, select, update, text, inspect)
from .order_runtime import create_app as order_app, Input, checksum, lock
from .identity_runtime import audit
from app.execution.spec.payment_contract import PaymentSimulationContract

SCHEMA = {'revision': '0004', 'parent': '0003', 'module': 'offline-payments-v1',
          'tables': ['simulated_payments', 'simulated_refunds', 'simulation_events'],
          'order_states': ['awaiting_payment', 'cancelled', 'expired', 'simulated_paid', 'simulated_refunded'],
          'money': 'simulation only; full admin refunds; no fulfillment'}


class Key(Input):
    idempotency_key: str = Field(min_length=16, max_length=80, pattern=r'^[A-Za-z0-9_-]+$')


class Outcome(Key):
    outcome: Literal['succeeded', 'failed', 'cancelled']
    amount_minor: StrictInt = Field(ge=0)
    currency: str = Field(pattern=r'^[A-Z]{3}$')


class RefundOutcome(Key):
    outcome: Literal['succeeded', 'failed']


def metadata():
    m = MetaData()
    Table('orders', m, Column('id', Integer, primary_key=True))
    Table('users', m, Column('id', Integer, primary_key=True))
    Table('simulated_payments', m, Column('id', Integer, primary_key=True),
          Column('order_id', Integer, ForeignKey('orders.id'), nullable=False, unique=True),
          Column('state', Text, nullable=False), Column('amount_minor', BigInteger, nullable=False),
          Column('currency', Text, nullable=False), Column('created_at', BigInteger, nullable=False),
          CheckConstraint("state IN ('pending','succeeded','failed','cancelled','expired','refunded')"),
          CheckConstraint('amount_minor >= 0'))
    Table('simulated_refunds', m, Column('id', Integer, primary_key=True),
          Column('payment_id', Integer, ForeignKey('simulated_payments.id'), nullable=False),
          Column('requested_by', Integer, ForeignKey('users.id'), nullable=False),
          Column('state', Text, nullable=False), Column('amount_minor', BigInteger, nullable=False),
          Column('created_at', BigInteger, nullable=False),
          CheckConstraint("state IN ('pending','succeeded','failed')"), CheckConstraint('amount_minor >= 0'))
    Table('simulation_events', m, Column('id', Integer, primary_key=True),
          Column('actor_id', Integer, ForeignKey('users.id'), nullable=False),
          Column('event_key', Text, nullable=False), Column('request_hash', Text, nullable=False),
          Column('resource_id', Integer, nullable=False), Column('created_at', BigInteger, nullable=False),
          UniqueConstraint('actor_id', 'event_key'))
    return m


def create_app(payment_path=None, order_path=None, identity_path=None, catalogue_path=None,
               database_url=None, clock=None, mail_sink=None):
    path = Path(payment_path or Path(__file__).with_name('payments.json'))
    config = PaymentSimulationContract.model_validate_json(path.read_text(encoding='utf-8'))
    schema = {**SCHEMA, 'rules': config.model_dump(mode='json')}
    digest = checksum(schema)
    if payment_path is None and json.loads((path.parent.parent/'migrations/0004.json').read_text(encoding='utf-8')) != schema:
        raise RuntimeError('Payment simulation migration manifest mismatch')
    m = metadata()
    payments, refunds, events = (m.tables[k] for k in SCHEMA['tables'])

    def install(conn, app):
        if conn.dialect.name != 'postgresql':
            raise RuntimeError('Payment simulator requires the supported PostgreSQL environment')
        revisions = dict(conn.execute(text('SELECT revision,checksum FROM projectforge_migrations')).all())
        if '0004' in revisions:
            if revisions['0004'] != digest: raise RuntimeError('Payment migration checksum mismatch')
            return
        if any(inspect(conn).has_table(k) for k in SCHEMA['tables']):
            raise RuntimeError('Unversioned payment tables; migration refused')
        # Upgrade only the exact phase-5 state constraint, retaining all totals/FK checks.
        checks = inspect(conn).get_check_constraints('orders')
        states = [c for c in checks if 'awaiting_payment' in c['sqltext'] and 'cancelled' in c['sqltext'] and 'expired' in c['sqltext']]
        if len(states) != 1: raise RuntimeError('Expected order state constraint is missing or ambiguous')
        name = conn.dialect.identifier_preparer.quote(states[0]['name'])
        conn.execute(text('ALTER TABLE orders DROP CONSTRAINT ' + name))
        conn.execute(text("ALTER TABLE orders ADD CONSTRAINT order_state_v4 CHECK (state IN ('awaiting_payment','cancelled','expired','simulated_paid','simulated_refunded'))"))
        m.create_all(conn, tables=[payments, refunds, events])
        conn.execute(text("CREATE UNIQUE INDEX one_open_or_successful_simulated_refund ON simulated_refunds(payment_id) WHERE state IN ('pending','succeeded')"))
        conn.execute(text('INSERT INTO projectforge_migrations (revision,checksum) VALUES (:r,:c)'), {'r': '0004', 'c': digest})

    app = order_app(order_path, identity_path, catalogue_path, database_url, clock, mail_sink,
                    migration_followups={'0004': digest}, install_extension=install)
    engine = app.state.engine
    orders = app.state.order_metadata.tables['orders']
    items = app.state.order_metadata.tables['order_items']
    variants = app.state.metadata.tables['variants']
    products = app.state.metadata.tables['products']
    now = app.state.order_now
    app.state.payment_simulator = True
    app.state.payment_metadata = m

    def payment_view(conn, row):
        p = conn.execute(select(payments).where(payments.c.order_id == row['id'])).mappings().first()
        return {'payment_mode': 'offline_simulator', 'payment_status': p['state'] if p else 'not_started',
                'simulation': dict(p) if p else None,
                'refunds': [dict(r) for r in conn.execute(select(refunds).where(refunds.c.payment_id == p['id']).order_by(refunds.c.id)).mappings()] if p else []}
    app.state.order_payment_view = payment_view

    def released(conn, row, state):
        conn.execute(update(payments).where(payments.c.order_id == row['id'], payments.c.state == 'pending').values(state=state))
    app.state.order_released = released

    def actor(request, administrative=False):
        _, user = app.state.identity_csrf(request, True)
        if administrative: app.state.identity_admin(request)
        app.state.identity_limited(request, 'simulation-'+request.scope['route'].name, str(user['id']), limit=30, window=300)
        return user

    def owned(conn, oid, user, administrative=False):
        row = conn.execute(select(orders).where(orders.c.id == oid)).mappings().first()
        if not row or (not administrative and row['user_id'] != user['id']): raise HTTPException(404, 'Order not found')
        return row

    def replay(conn, user, key, fingerprint):
        old = conn.execute(select(events).where(events.c.actor_id == user['id'], events.c.event_key == key)).mappings().first()
        if old and old['request_hash'] != fingerprint: raise HTTPException(409, 'Simulation key was used for a different request')
        return old

    def record(conn, user, key, fingerprint, rid, action):
        conn.execute(events.insert().values(actor_id=user['id'], event_key=key, request_hash=fingerprint, resource_id=rid, created_at=now()))
        audit(conn, app.state.identity_metadata, action, user['id'], 'simulation', rid, now())

    def view(conn, pid):
        p = dict(conn.execute(select(payments).where(payments.c.id == pid)).mappings().one())
        return {**p, 'mode': 'offline_simulator', 'real_money_collected': False}

    def prepare():
        # Commit expiry before entering a request transaction: rejected late outcomes
        # must not roll back the release of expired stock.
        app.state.expire_reservations()

    @app.post('/api/simulation/orders/{order_id}/payment')
    def start(order_id: int, payload: Key, request: Request):
        user = actor(request); prepare()
        fp = checksum(['start', order_id])
        with engine.begin() as conn:
            lock(conn); row = owned(conn, order_id, user)
            old = replay(conn, user, payload.idempotency_key, fp)
            if old: return view(conn, old['resource_id'])
            p = conn.execute(select(payments).where(payments.c.order_id == order_id)).mappings().first()
            if row['state'] != 'awaiting_payment' or row['expires_at'] <= now(): raise HTTPException(409, 'Order cannot start a simulated payment')
            if p: pid = p['id']
            else:
                pid = conn.execute(payments.insert().values(order_id=order_id, state='pending', amount_minor=row['total_minor'], currency=row['currency'], created_at=now())).inserted_primary_key[0]
            record(conn, user, payload.idempotency_key, fp, pid, 'simulation_started')
            return view(conn, pid)

    @app.post('/api/simulation/payments/{payment_id}/resolve')
    def resolve(payment_id: int, payload: Outcome, request: Request):
        user = actor(request); prepare()
        fp = checksum(['resolve', payment_id, payload.model_dump(exclude={'idempotency_key'})])
        with engine.begin() as conn:
            lock(conn)
            p = conn.execute(select(payments).where(payments.c.id == payment_id)).mappings().first()
            if not p: raise HTTPException(404, 'Simulation not found')
            row = owned(conn, p['order_id'], user)
            if replay(conn, user, payload.idempotency_key, fp): return view(conn, payment_id)
            if payload.amount_minor != row['total_minor'] or payload.currency != row['currency']:
                raise HTTPException(409, 'Simulation amount or currency does not match the order')
            if p['state'] != 'pending' or row['state'] != 'awaiting_payment' or row['expires_at'] <= now():
                raise HTTPException(409, 'Simulation is already resolved or reservation expired')
            conn.execute(update(payments).where(payments.c.id == payment_id).values(state=payload.outcome))
            if payload.outcome == 'succeeded':
                conn.execute(update(orders).where(orders.c.id == row['id']).values(state='simulated_paid'))
            else:
                restore(conn, row)
                conn.execute(update(orders).where(orders.c.id == row['id']).values(state='cancelled'))
            record(conn, user, payload.idempotency_key, fp, payment_id, 'simulation_' + payload.outcome)
            return view(conn, payment_id)

    def restore(conn, row):
        for item in conn.execute(select(items).where(items.c.order_id == row['id'])).mappings():
            variant = conn.execute(select(variants).where(variants.c.id == item['variant_id'])).mappings().one()
            conn.execute(update(variants).where(variants.c.id == item['variant_id']).values(stock_quantity=variants.c.stock_quantity + item['quantity']))
            conn.execute(update(products).where(products.c.id == variant['product_id']).values(version=products.c.version + 1))

    @app.post('/api/admin/simulation/payments/{payment_id}/refund')
    def refund(payment_id: int, payload: Key, request: Request):
        user = actor(request, True)
        fp = checksum(['refund', payment_id])
        with engine.begin() as conn:
            lock(conn)
            old = replay(conn, user, payload.idempotency_key, fp)
            if old: return dict(conn.execute(select(refunds).where(refunds.c.id == old['resource_id'])).mappings().one())
            p = conn.execute(select(payments).where(payments.c.id == payment_id)).mappings().first()
            if not p: raise HTTPException(404, 'Simulation not found')
            if p['state'] != 'succeeded': raise HTTPException(409, 'Only a successful simulated payment can be refunded')
            if conn.execute(select(refunds.c.id).where(refunds.c.payment_id == payment_id, refunds.c.state.in_(['pending', 'succeeded']))).first():
                raise HTTPException(409, 'Refund is pending or already completed')
            rid = conn.execute(refunds.insert().values(payment_id=payment_id, requested_by=user['id'], state='pending', amount_minor=p['amount_minor'], created_at=now())).inserted_primary_key[0]
            record(conn, user, payload.idempotency_key, fp, rid, 'simulation_refund_requested')
            return dict(conn.execute(select(refunds).where(refunds.c.id == rid)).mappings().one())

    @app.post('/api/admin/simulation/refunds/{refund_id}/resolve')
    def resolve_refund(refund_id: int, payload: RefundOutcome, request: Request):
        user = actor(request, True)
        fp = checksum(['refund_outcome', refund_id, payload.outcome])
        with engine.begin() as conn:
            lock(conn)
            r = conn.execute(select(refunds).where(refunds.c.id == refund_id)).mappings().first()
            if not r: raise HTTPException(404, 'Refund not found')
            if replay(conn, user, payload.idempotency_key, fp): return dict(r)
            p = conn.execute(select(payments).where(payments.c.id == r['payment_id'])).mappings().one()
            if r['state'] != 'pending' or p['state'] != 'succeeded': raise HTTPException(409, 'Refund is already resolved')
            conn.execute(update(refunds).where(refunds.c.id == refund_id).values(state=payload.outcome))
            if payload.outcome == 'succeeded':
                row = owned(conn, p['order_id'], user, True)
                if row['state'] != 'simulated_paid': raise HTTPException(409, 'Order state does not allow refund')
                restore(conn, row)
                conn.execute(update(orders).where(orders.c.id == row['id']).values(state='simulated_refunded'))
                conn.execute(update(payments).where(payments.c.id == p['id']).values(state='refunded'))
            record(conn, user, payload.idempotency_key, fp, refund_id, 'simulation_refund_' + payload.outcome)
            return dict(conn.execute(select(refunds).where(refunds.c.id == refund_id)).mappings().one())
    return app
