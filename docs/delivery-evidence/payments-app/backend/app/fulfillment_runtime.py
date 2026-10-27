"""Manual demo delivery tracking, independent of payment state and stock counts."""
from typing import Literal
from fastapi import HTTPException, Request
from pydantic import BaseModel, ConfigDict
from sqlalchemy import MetaData, Table, Column, Integer, BigInteger, Text, ForeignKey, CheckConstraint, select, text, inspect
from .identity_runtime import audit

SCHEMA = {'revision': '0005_delivery', 'module': 'manual-delivery-v1',
          'states': ['not_packed', 'packed', 'shipped', 'delivered'],
          'policy': 'paid demo orders only; no returns after packing; no stock mutations'}


class DeliveryUpdate(BaseModel):
    model_config = ConfigDict(extra='forbid')
    expected_status: Literal['not_packed', 'packed', 'shipped', 'delivered']
    status: Literal['packed', 'shipped', 'delivered']


def configure(app):
    # Imported here to avoid a module-initialization cycle.
    from .order_runtime import checksum, lock
    m = MetaData()
    Table('orders', m, Column('id', Integer, primary_key=True))
    Table('users', m, Column('id', Integer, primary_key=True))
    deliveries = Table('order_fulfillment', m,
        Column('order_id', Integer, ForeignKey('orders.id'), primary_key=True),
        Column('status', Text, nullable=False),
        Column('updated_by', Integer, ForeignKey('users.id'), nullable=False),
        Column('updated_at', BigInteger, nullable=False),
        CheckConstraint("status IN ('packed','shipped','delivered')"))
    digest = checksum(SCHEMA)
    orders = app.state.order_metadata.tables['orders']

    def status(conn, oid):
        return conn.execute(select(deliveries.c.status).where(deliveries.c.order_id == oid)).scalar_one_or_none() or 'not_packed'

    def block_refund(conn, oid):
        if status(conn, oid) != 'not_packed':
            raise HTTPException(409, 'Packing has started. Returns after packing are not supported.')

    def view(conn, row):
        record = conn.execute(select(deliveries).where(deliveries.c.order_id == row['id'])).mappings().first()
        payment = app.state.order_payment_view(conn, row)
        pending = any(r['state'] in ('creating', 'pending', 'processed', 'succeeded')
                      for r in payment.get('refunds', []) + payment.get('provider_refunds', []))
        eligible = row['state'] in ('simulated_paid', 'razorpay_test_paid') and payment['payment_status'] in ('succeeded', 'captured') and not pending
        current = record['status'] if record else 'not_packed'
        return {'status': current, 'updated_at': record['updated_at'] if record else None,
                'next_status': {'not_packed': 'packed', 'packed': 'shipped', 'shipped': 'delivered'}.get(current) if eligible else None,
                'demo_only': True}

    def install(conn):
        revisions = dict(conn.execute(text('SELECT revision,checksum FROM projectforge_migrations')).all())
        if SCHEMA['revision'] in revisions:
            if revisions[SCHEMA['revision']] != digest: raise RuntimeError('Delivery migration checksum mismatch')
            return
        if inspect(conn).has_table('order_fulfillment'): raise RuntimeError('Unversioned delivery table; migration refused')
        m.create_all(conn, tables=[deliveries])
        conn.execute(text('INSERT INTO projectforge_migrations (revision,checksum) VALUES (:r,:c)'), {'r': SCHEMA['revision'], 'c': digest})

    @app.post('/api/admin/orders/{order_id}/fulfillment')
    def advance(order_id: int, payload: DeliveryUpdate, request: Request):
        _, user = app.state.identity_csrf(request, True, True)
        with app.state.engine.begin() as conn:
            lock(conn)
            row = conn.execute(select(orders).where(orders.c.id == order_id)).mappings().first()
            if row is None: raise HTTPException(404, 'Order not found')
            current = view(conn, row)
            next_states = {'not_packed': 'packed', 'packed': 'shipped', 'shipped': 'delivered'}
            if next_states.get(payload.expected_status) != payload.status:
                raise HTTPException(409, 'Delivery statuses must advance one step at a time')
            # Retrying the same completed step is a no-op, including after a lost response.
            if current['status'] == payload.status: return current
            if current['status'] != payload.expected_status:
                raise HTTPException(409, 'Delivery status changed. Refresh before continuing.')
            if current['next_status'] != payload.status:
                raise HTTPException(409, 'Delivery requires a paid order without an active refund')
            values = {'status': payload.status, 'updated_by': user['id'], 'updated_at': app.state.order_now()}
            if current['status'] == 'not_packed': conn.execute(deliveries.insert().values(order_id=order_id, **values))
            else: conn.execute(deliveries.update().where(deliveries.c.order_id == order_id).values(**values))
            audit(conn, app.state.identity_metadata, 'delivery_' + payload.status, user['id'], 'order', order_id, app.state.order_now())
            return view(conn, row)

    app.state.fulfillment_view = view
    app.state.fulfillment_status = status
    app.state.fulfillment_block_refund = block_refund
    return install
