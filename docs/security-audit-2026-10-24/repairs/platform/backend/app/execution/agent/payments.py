"""Reviewed offline simulator layered on the existing order generator."""
import json
from pathlib import Path
from app.execution.agent import orders
from app.execution.agent.payment_runtime import SCHEMA
from app.execution.spec.build_spec_models import APIEndpointDef, TargetFileDef

ROUTES = (('POST', '/api/simulation/orders/{order_id}/payment'),
          ('POST', '/api/simulation/payments/{payment_id}/resolve'),
          ('POST', '/api/admin/simulation/payments/{payment_id}/refund'),
          ('POST', '/api/admin/simulation/refunds/{refund_id}/resolve'))


def base_spec(spec):
    base = spec.model_copy(deep=True)
    base.payment_simulation_contract = None
    base.requirements = []
    return base


def validate_scope(spec):
    if not spec.payment_simulation_contract:
        raise ValueError('PAYMENT_SIMULATOR requires an explicit offline simulator contract')
    if spec.tech_stack.primary_database.lower() != 'postgresql':
        raise ValueError('Payment simulator requires PostgreSQL')
    orders.validate_scope(base_spec(spec))
    for req in spec.requirements:
        if req.source.value == 'USER' and req.dimension in ('functional', 'functional_requirements'):
            if any(term in req.description.lower() for term in ('razorpay', 'live payment', 'real payment', 'card details', 'subscription', 'marketplace', 'fulfillment', 'partial refund', 'upload')):
                raise ValueError('Requirement exceeds offline simulator scope: ' + req.id)


def sources(spec):
    validate_scope(spec)
    output = orders.sources(base_spec(spec))
    root = Path(__file__).parent
    contract = (root.parent/'spec/payment_contract.py').read_text(encoding='utf-8').replace('from app.execution.spec.commerce_contract import StrictContract', 'StrictContract = Input')
    runtime = (root/'payment_runtime.py').read_text(encoding='utf-8').replace('from app.execution.spec.payment_contract import PaymentSimulationContract', contract)
    output['backend/app/payment_runtime.py'] = runtime
    output['backend/app/payments.json'] = spec.payment_simulation_contract.model_dump_json(indent=2)
    output['backend/migrations/0004.json'] = json.dumps({**SCHEMA, 'rules': spec.payment_simulation_contract.model_dump(mode='json')}, indent=2)
    output['backend/app/main.py'] = 'from .payment_runtime import create_app\napp=create_app()\n'
    output['frontend/src/Payments.tsx'] = (root/'order_templates/Payments.tsx').read_text(encoding='utf-8')
    ui = json.loads(output['frontend/src/ui-contract.json'])
    ui['payments'] = {'version': 1, 'mode': 'offline_simulator', 'ids': {'panel': 'payment-simulator', 'notice': 'payment-notice', 'status': 'payment-status'}}
    output['frontend/src/ui-contract.json'] = json.dumps(ui, indent=2)
    page = output['frontend/src/Orders.tsx']
    page = "import Payments from './Payments';\n" + page
    page = page.replace('payment_status:string};', 'payment_status:string;simulation:{id:number;state:string;amount_minor:number;currency:string}|null;refunds:{id:number;state:string}[]};')
    page = page.replace('Payments and fulfillment are not enabled.', 'Offline payment simulation is enabled. No real money is collected; fulfillment is disabled.')
    page = page.replace('</article>)}</section>;', '<Payments order={o} admin={admin} reload={load}/></article>)}</section>;')
    output['frontend/src/Orders.tsx'] = page
    output['frontend/src/App.tsx'] = output['frontend/src/App.tsx'].replace('Payments are disabled.', 'Offline payment simulation only. No real money is collected.')
    output['frontend/src/identity.css'] += '\n.payment-panel{flex-basis:100%;border:1px solid #b8c5a7;background:#f4f5ec;padding:18px;border-radius:8px}.payment-panel .order-actions{margin:12px 0}.payment-panel p{overflow-wrap:anywhere}.payment-panel button{min-height:44px}.payment-notice{font-weight:650;color:#405235}\n'
    readme = output['README.md']
    readme = readme.replace('# Generated catalogue', '# Generated store with offline payment simulation')
    readme = readme.replace('This phase is a public, read-only catalogue.\nAccounts, administration, carts, checkout and payments are not implemented.', 'Includes catalogue, accounts, administration, cart, orders and an offline payment simulator.\nReal payments and fulfillment are not implemented.')
    readme = readme.replace('Stock is a catalogue\nsnapshot; reservation and overselling protection are a later phase.', 'Cart checkout reserves available stock; see the order and simulator sections below.')
    readme = readme.replace('Orders, cart and payments are not implemented.', 'Real payment collection is not implemented; the simulator is described below.')
    readme = readme.replace('## Unpaid orders and inventory reservations', '## Orders and inventory reservations')
    readme = readme.replace('Payments, fulfillment and refunds remain disabled.', 'Real payments, fulfillment and real refunds remain disabled.')
    output['README.md'] = readme
    output['README.md'] += '''
## Offline payment simulator
This build uses PAYMENT_SIMULATOR, not a payment provider. Every outcome is explicitly
simulated. No money, card details, provider credentials, webhooks or external requests
are involved. Do not expose this demo as a real checkout or count it as gateway evidence.
PostgreSQL migration 0004 preserves 0001–0003 and adds simulation records and order states.
Visit /orders to start a pending simulation, then choose success, failure or cancellation.
A failed/cancelled simulation cancels the order and restores stock once. Create a NEW
order to retry after a terminal outcome. A successful simulation consumes its reservation
and never expires. Ordinary cancellation is then forbidden; an admin full refund is required.
Visit /admin/orders as an administrator to start a full simulated refund, then simulate
success or failure. Failed refunds may be retried with a new key. Successful refunds
restore stock once because fulfillment is disabled. Partial refunds/returns are unsupported.
All mutations require session + CSRF + ownership or admin permission. Amount/currency
are copied from the server order; mismatches and contradictory terminal outcomes fail.
Retries must use the same idempotency key and request. The UI stores only request metadata
in sessionStorage, scoped to the order. Resolve/discard ambiguous requests explicitly.
Simulation audit and event records persist in PostgreSQL. Retention/cleanup is not implemented.
Each simulation action is limited to 30 requests per account per five-minute window,
with shared IP/global caps; rejected attempts return HTTP 429 and Retry-After.
Live payments cannot be enabled by editing this contract; a separate future adapter is required.
'''
    return output


def prepare_spec(spec):
    result = spec.model_copy(deep=True)
    result.source_generation_strategy = 'PAYMENT_SIMULATOR'
    result.generation_mode = 'MODEL'
    result.api_endpoints = orders.prepare_spec(base_spec(spec)).api_endpoints + [
        APIEndpointDef(endpoint_id='simulation-'+str(i), method=method, path=path,
                       description='Offline simulation only; no real payment', auth_required=True)
        for i, (method, path) in enumerate(ROUTES)]
    result.files_to_create = [TargetFileDef(file_path=path, description='Reviewed offline simulation: '+path,
                            target_module='backend' if path.startswith('backend/') else 'frontend',
                            is_test_file='/tests/' in path, traceable_requirements=[r.id for r in result.requirements])
                            for path in sources(result)]
    return result
