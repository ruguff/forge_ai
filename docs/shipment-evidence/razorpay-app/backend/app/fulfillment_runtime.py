"""Manual demo delivery tracking, independent of payment state and stock counts."""
from typing import Literal
import re
import unicodedata
from fastapi import HTTPException, Request, Path
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import MetaData, Table, Column, Integer, BigInteger, Text, ForeignKey, CheckConstraint, select, text, inspect
from .identity_runtime import audit

SCHEMA = {'revision': '0005_delivery', 'module': 'manual-delivery-v1',
          'states': ['not_packed', 'packed', 'shipped', 'delivered'],
          'policy': 'paid demo orders only; no returns after packing; no stock mutations'}

TRACKING_SCHEMA = {'revision': '0006_tracking', 'module': 'manual-shipping-details-v1',
                   'parent': '0005_delivery', 'courier_max_length': 100, 'tracking_max_length': 100,
                   'policy': 'admin edits paid orders before delivery; optimistic version; no external requests'}


class ShippingDetailsUpdate(BaseModel):
    model_config = ConfigDict(extra='forbid')
    expected_version: int = Field(strict=True, ge=0)
    courier_name: str = Field(min_length=1, max_length=100)
    tracking_number: str = Field(min_length=1, max_length=100)

    @field_validator('courier_name', 'tracking_number', mode='before')
    @classmethod
    def clean_text(cls, value):
        if not isinstance(value, str) or any(unicodedata.category(c).startswith('C') for c in value):
            raise ValueError('Use plain text without control characters')
        return value.strip()

    @field_validator('courier_name')
    @classmethod
    def courier_characters(cls, value):
        if any(not (unicodedata.category(c)[0] in 'LMN' or c in " .&'()-") for c in value):
            raise ValueError('Use a courier name with letters, numbers, spaces or ordinary punctuation')
        if not any(c.isalnum() for c in value):
            raise ValueError('Enter a courier name')
        return value

    @field_validator('tracking_number')
    @classmethod
    def tracking_characters(cls, value):
        if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9 ._/-]{0,99}', value):
            raise ValueError('Use a tracking number with letters, numbers, spaces, hyphens, dots, underscores or slashes')
        return value


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
    shipments = Table('order_shipping_details', m,
        Column('order_id', Integer, ForeignKey('orders.id'), primary_key=True),
        Column('courier_name', Text, nullable=False),
        Column('tracking_number', Text, nullable=False),
        Column('version', Integer, nullable=False),
        Column('updated_by', Integer, ForeignKey('users.id'), nullable=False),
        Column('updated_at', BigInteger, nullable=False),
        CheckConstraint('version >= 1'),
        CheckConstraint('length(courier_name) BETWEEN 1 AND 100'),
        CheckConstraint('length(tracking_number) BETWEEN 1 AND 100'))
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
        shipment = conn.execute(select(shipments).where(shipments.c.order_id == row['id'])).mappings().first()
        return {'status': current, 'updated_at': record['updated_at'] if record else None,
                'next_status': {'not_packed': 'packed', 'packed': 'shipped', 'shipped': 'delivered'}.get(current) if eligible else None,
                'shipping_details': {key: shipment[key] for key in ('courier_name', 'tracking_number', 'version', 'updated_at')} if shipment else None,
                'can_edit_shipping': eligible and current != 'delivered',
                'demo_only': True}

    def install(conn):
        revisions = dict(conn.execute(text('SELECT revision,checksum FROM projectforge_migrations')).all())
        for schema, table, expected in ((SCHEMA, deliveries, digest), (TRACKING_SCHEMA, shipments, checksum(TRACKING_SCHEMA))):
            if schema['revision'] in revisions:
                if revisions[schema['revision']] != expected: raise RuntimeError('Delivery migration checksum mismatch')
                continue
            if inspect(conn).has_table(table.name): raise RuntimeError('Unversioned delivery table; migration refused')
            m.create_all(conn, tables=[table])
            conn.execute(text('INSERT INTO projectforge_migrations (revision,checksum) VALUES (:r,:c)'), {'r': schema['revision'], 'c': expected})

    @app.get('/api/orders/{order_id}/shipment')
    def customer_shipment(request: Request, order_id: int = Path(ge=1, le=2147483647)):
        _, user = app.state.identity_session(request, True)
        with app.state.engine.begin() as conn:
            lock(conn)
            app.state.order_expire(conn)
            row = conn.execute(select(orders).where(orders.c.id == order_id, orders.c.user_id == user['id'])).mappings().first()
            if row is None: raise HTTPException(404, 'Shipment not found')
            delivery = view(conn, row)
            # Return a customer projection, never the admin audit log or actor IDs.
            records = app.state.identity_metadata.tables['audit_records']
            milestones = {'delivery_packed': 'packed', 'delivery_shipped': 'shipped', 'delivery_delivered': 'delivered'}
            events = conn.execute(select(records.c.action, records.c.created_at).where(
                records.c.resource == 'order', records.c.resource_id == str(order_id),
                records.c.action.in_(milestones)).order_by(records.c.id)).mappings()
            history = [{'status': 'placed', 'recorded_at': row['created_at']}]
            seen = set()
            for event in events:
                step = milestones[event['action']]
                if step not in seen:
                    history.append({'status': step, 'recorded_at': event['created_at']})
                    seen.add(step)
            if row['state'] in ('cancelled', 'expired'): availability = row['state']
            elif row['state'] in ('simulated_refunded', 'razorpay_test_refunded'): availability = 'refunded'
            elif delivery['status'] == 'delivered': availability = 'delivered'
            elif row['state'] == 'awaiting_payment': availability = 'awaiting_payment'
            elif not delivery['can_edit_shipping']: availability = 'on_hold'
            else: availability = 'active'
            return {'order_id': order_id, 'availability': availability, 'status': delivery['status'],
                    'updated_at': delivery['updated_at'], 'shipping_details': delivery['shipping_details'],
                    'history': history, 'update_source': 'store_manual', 'estimated_delivery': None}

    @app.post('/api/admin/orders/{order_id}/shipping-details')
    def save_shipping(order_id: int, payload: ShippingDetailsUpdate, request: Request):
        _, user = app.state.identity_csrf(request, True, True)
        with app.state.engine.begin() as conn:
            lock(conn)
            row = conn.execute(select(orders).where(orders.c.id == order_id)).mappings().first()
            if row is None: raise HTTPException(404, 'Order not found')
            current = view(conn, row)
            if not current['can_edit_shipping']:
                raise HTTPException(409, 'Shipping details require a paid order without an active refund and cannot change after delivery')
            saved = current['shipping_details']
            version = saved['version'] if saved else 0
            # A lost-response retry can confirm exactly the most recent update.
            if saved and payload.expected_version in (version, version - 1) and all(
                    saved[key] == getattr(payload, key) for key in ('courier_name', 'tracking_number')):
                return current
            if payload.expected_version != version:
                raise HTTPException(409, 'Shipping details changed. Refresh the order before saving again.')
            values = {'courier_name': payload.courier_name, 'tracking_number': payload.tracking_number,
                      'version': version + 1, 'updated_by': user['id'], 'updated_at': app.state.order_now()}
            if saved: conn.execute(shipments.update().where(shipments.c.order_id == order_id).values(**values))
            else: conn.execute(shipments.insert().values(order_id=order_id, **values))
            audit(conn, app.state.identity_metadata, 'shipping_details_updated', user['id'], 'order', order_id, app.state.order_now())
            return view(conn, row)

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
    app.state.shipping_details_version = 1
    return install
