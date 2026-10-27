"""Strategy and runtime-manifest checks for the reviewed unpaid-order module."""
import json

import pytest

from app.execution.agent.orders import ROUTES, prepare_spec, sources, validate_scope
from app.execution.sandbox.order_browser import SOURCE as BROWSER_SOURCE
from app.execution.spec.catalogue_example import example_spec
from app.execution.spec.identity_contract import IdentityContract
from app.execution.spec.order_contract import OrderContract


def spec():
    value = example_spec()
    value.identity_contract = IdentityContract(
        public_origin='http://127.0.0.1:3001', allow_local_http=True)
    value.tech_stack.auth_provider = 'session'
    value.order_contract = OrderContract(
        tax_basis_points=500, shipping_minor=500, discount_basis_points=0,
        policy_label='Synthetic test-only rules')
    return value


def test_orders_compiles_to_bounded_reviewed_module_and_migrations():
    prepared = prepare_spec(spec())
    generated = sources(prepared)
    paths = [item.file_path for item in prepared.files_to_create]
    assert prepared.source_generation_strategy == 'ORDERS'
    assert len(paths) == len(set(paths)) == len(generated) <= 40
    assert {'backend/migrations/0001.json', 'backend/migrations/0002.json',
            'backend/migrations/0003.json'} <= generated.keys()
    assert json.loads(generated['backend/migrations/0003.json'])['parent'] == '0002'
    assert json.loads(generated['backend/app/orders.json'])['policy_label'] == 'Synthetic test-only rules'
    assert all(not path.startswith('backend/tests/') or path.endswith('.py') for path in paths)
    for path, source in generated.items():
        if path.endswith('.py'):
            compile(source, path, 'exec')
    api = {(endpoint.method, endpoint.path) for endpoint in prepared.api_endpoints}
    assert set(ROUTES) <= api
    runtime = generated['backend/app/order_runtime.py']
    assert 'pg_advisory_xact_lock(681072015)' in runtime
    assert 'idempotency_key' in runtime and 'address_snapshot' in runtime


@pytest.mark.parametrize('phrase', [
    'Implement Razorpay payments and collect payment',
    'Add customer refunds and paid order handling',
    'Create a multi-vendor marketplace',
    'Add file uploads and product fulfillment',
])
def test_orders_rejects_features_outside_unpaid_single_store_scope(phrase):
    value = spec()
    value.requirements[0].description = phrase
    with pytest.raises(ValueError, match='exceeds unpaid order phase'):
        validate_scope(value)


def test_orders_requires_explicit_tax_shipping_and_session_identity():
    value = spec()
    value.order_contract = None
    with pytest.raises(ValueError, match='explicit shipping/tax/discount'):
        validate_scope(value)
    value = spec()
    value.tech_stack.auth_provider = 'JWT'
    with pytest.raises(ValueError, match='server-side sessions'):
        validate_scope(value)


def test_platform_browser_gate_source_is_valid_python():
    compile(BROWSER_SOURCE, 'test_order_browser.py', 'exec')
