"""Separate test-provider composition; never substitutes simulated verification."""
import json
from pathlib import Path
from app.execution.agent import orders
from app.execution.agent.razorpay_runtime import SCHEMA
from app.execution.spec.build_spec_models import APIEndpointDef, TargetFileDef


def base_spec(spec):
    base = spec.model_copy(deep=True)
    base.razorpay_test_contract = None
    base.requirements = []
    return base


def validate_scope(spec):
    if not spec.razorpay_test_contract or spec.payment_simulation_contract:
        raise ValueError('RAZORPAY_TEST requires an explicit test contract and excludes the simulator')
    if spec.tech_stack.primary_database.lower() != 'postgresql' or not spec.catalogue_contract or spec.catalogue_contract.currency != 'INR':
        raise ValueError('Razorpay test scope requires PostgreSQL and INR')
    orders.validate_scope(base_spec(spec))
    for req in spec.requirements:
        if req.source.value == 'USER' and req.dimension in ('functional', 'functional_requirements'):
            if any(term in req.description.lower() for term in ('live payment', 'real payment', 'card details', 'subscription', 'marketplace', 'fulfillment', 'partial refund', 'upload')):
                raise ValueError('Requirement exceeds Razorpay test scope: '+req.id)


def sources(spec):
    validate_scope(spec)
    output = orders.sources(base_spec(spec)); root = Path(__file__).parent
    output['backend/app/fulfillment_runtime.py'] = (root/'fulfillment_runtime.py').read_text(encoding='utf-8')
    output['frontend/src/Fulfillment.tsx'] = (root/'order_templates/Fulfillment.tsx').read_text(encoding='utf-8')
    page = "import Fulfillment,{type Delivery} from './Fulfillment';\n" + output['frontend/src/Orders.tsx']
    page = page.replace('type Order={id:number;', 'type Order={fulfillment?:Delivery;id:number;')
    page = page.replace('</article>)}</section>;', '<Fulfillment order={o} admin={admin} reload={load}/></article>)}</section>;')
    output['frontend/src/Orders.tsx'] = page
    contract = (root.parent/'spec/razorpay_contract.py').read_text(encoding='utf-8').replace('from app.execution.spec.commerce_contract import StrictContract', 'StrictContract = Input')
    output['backend/app/razorpay_runtime.py'] = (root/'razorpay_runtime.py').read_text(encoding='utf-8').replace('from app.execution.spec.razorpay_contract import RazorpayTestContract', contract)
    output['backend/app/razorpay_client.py'] = (root/'razorpay_client.py').read_text(encoding='utf-8')
    output['backend/app/razorpay.json'] = spec.razorpay_test_contract.model_dump_json(indent=2)
    output['backend/migrations/0004_razorpay_test.json'] = json.dumps({**SCHEMA, 'rules': spec.razorpay_test_contract.model_dump(mode='json')}, indent=2)
    output['backend/app/main.py'] = 'from .razorpay_runtime import create_app\napp=create_app()\n'
    output['frontend/src/RazorpayCheckout.tsx'] = (root/'order_templates/RazorpayCheckout.tsx').read_text(encoding='utf-8')
    ui = json.loads(output['frontend/src/ui-contract.json'])
    ui['payments'] = {'version':1,'mode':'razorpay_test','ids':{'panel':'razorpay-test','notice':'payment-notice','status':'payment-status'}}
    ui['delivery'] = {'version': 2, 'mode': 'manual', 'ids': {'status': 'delivery-status', 'details': 'shipping-details', 'form': 'shipping-form'}}
    output['frontend/src/ui-contract.json'] = json.dumps(ui, indent=2)
    page = "import RazorpayCheckout from './RazorpayCheckout';\n"+output['frontend/src/Orders.tsx']
    page = page.replace('payment_status:string};', 'payment_status:string;provider_payment:{state:string}|null;provider_refunds:{id:number;state:string}[]};')
    page = page.replace('Payments and fulfillment are not enabled.', 'Razorpay TEST MODE only. Manual demo delivery tracking is available.')
    page = page.replace('· No payment collected</p>', "· {o.payment_status==='not_started'?'No payment collected':'Test provider status: '+o.payment_status}</p>")
    page = page.replace('</article>)}</section>;', '<RazorpayCheckout order={o} admin={admin} reload={load}/></article>)}</section>;')
    output['frontend/src/Orders.tsx'] = page
    output['frontend/src/App.tsx'] = output['frontend/src/App.tsx'].replace('Payments are disabled.', 'Razorpay TEST MODE only. No live payments.')
    output['frontend/src/identity.css'] += '\n.payment-panel{flex-basis:100%;border:1px solid #b8c5a7;background:#f4f5ec;padding:18px;border-radius:8px}.payment-panel p{overflow-wrap:anywhere}.payment-panel button{min-height:44px}.payment-panel .order-actions{margin:12px 0}.payment-notice{font-weight:650;color:#405235}\n'
    output['backend/reconcile_payment.py'] = '''"""Explicit operator recovery, using configured server credentials only."""
import asyncio,sys
from app.main import app
async def main():
    async with app.router.lifespan_context(app):
        print(await asyncio.to_thread(app.state.reconcile_razorpay_order,int(sys.argv[1])))
if __name__=='__main__':asyncio.run(main())
'''
    output['README.md'] += '''
## Razorpay TEST integration (supersedes earlier unpaid-only capability notices)
This build includes accounts, catalogue, carts and reserved orders plus a separate
Razorpay test adapter. No live payments, fulfillment or partial refunds. Real provider
verification is UNVERIFIED until a test-account checkout and webhook round trip pass.
Mocked API checks are not proof of provider integration. Never enter real card data.

Configure privately in the backend process environment (never in frontend/.env,
BuildSpec, prompts, test fixtures, reports or source control):
RAZORPAY_TEST_ENABLED=1
RAZORPAY_TEST_KEY_ID=<your rzp_test_ key ID>
RAZORPAY_TEST_KEY_SECRET=<your test key secret>
RAZORPAY_TEST_WEBHOOK_SECRET=<separate strong secret of at least 16 characters>
RAZORPAY_TEST_ACCOUNT_ID=<your acc_ account ID>
Live key IDs are rejected. No configurable provider URL exists. The public key ID
is passed to official provider Checkout; all secrets remain on the server.
Configure automatic test capture in your account; authorized alone never marks paid.
The official Checkout script and provider API require internet access. A fresh demo
without credentials will display an explicit unavailable error and cannot mark paid.

Use a NEW PostgreSQL database, or migrate a phase-5 ORDERS database after backup.
Migration 0004_razorpay_test is a separate branch from simulator 0004; switching a
simulator database is rejected. Startup applies a checksummed transactional migration.
On /orders choose Open Razorpay test checkout. A callback signature is necessary but
insufficient: backend fetches provider order/payment and verifies identity, amount,
currency and capture. Refresh provider status reconciles delayed/lost results.
Administrators use /admin/orders for reconciliation and full test refunds. The same
saved refund key must be retried after an ambiguous response; never discard it to
force another refund. Processed refunds restore stock once because fulfillment is off.
Late captures after cancellation/expiry are flagged late_capture and require refund;
they never reclaim released inventory. Dashboard-issued refunds require operator review.

Configure /api/razorpay/webhook on an explicitly approved public HTTPS endpoint with
payment.authorized, payment.captured, payment.failed, order.paid, refund.created,
refund.processed and refund.failed events. localhost cannot receive provider callbacks.
Do not expose the local development server automatically. HMAC covers raw request bytes.
Duplicate event IDs are persisted; notifications cause fresh provider reconciliation.
No raw payment/card payload is stored. Keep old webhook secrets/retries in mind when
rotating credentials: automated multi-secret rotation is not implemented.

Operator recovery from backend/: python reconcile_payment.py ORDER_ID
Reconciliation is explicit (UI/CLI/webhooks), not a scheduled background worker.
An uncertain order create searches the saved unique receipt and never blindly creates
another order. If no match appears, leave pending for operator/provider investigation.
Refund retries use a persisted X-Refund-Idempotency key and identical payload.
Only full INR orders of at least 100 paise are supported. Retention/cleanup, fulfillment,
partial refunds, tax legality and production release checks are outside this phase.
'''
    output['README.md'] += '\n## Manual demo delivery tracking\nOn /admin/orders, an authenticated administrator can advance a settled demo order\nthrough Not packed -> Packed -> Shipped -> Delivered. Customers see the saved\nstatus in /orders. These are manual demo records, not courier dispatch evidence.\nOnly paid orders without active refunds can advance. Skips, backwards/stale updates,\ncustomer writes and invalid CSRF requests are rejected. Retries of the same completed\nstep have no additional effect. Changes are audited and survive restart.\nMigration 0005_delivery adds order_fulfillment without changing previous migrations\nor resetting existing data. Start the updated backend (or run migrate.py) to apply it.\nRefund initiation is blocked once packing begins because returns are not implemented.\nDelivery changes never modify payment status or stock. No courier integration,\ntracking numbers, notifications, returns workflow or live fulfillment is included.\nThis section supersedes earlier statements that all fulfillment tracking is disabled.\n'
    output['README.md'] += '\n## Courier and tracking number\nAdministrators can save a courier name and tracking number on /admin/orders for a\npaid order without an active refund, until the order is delivered. Customers see\nthe saved values on their own /orders page. Both fields are required when saving;\neach accepts at most 100 characters. These are manually entered details, with no\ncourier booking, remote tracking lookup or automatic status updates.\nExisting delivery transitions remain available even if tracking details have not\nbeen entered. Delivered records are read-only. Refresh before retrying a stale edit.\nMigration 0006_tracking adds order_shipping_details and preserves existing records\nand migration checksums. Restart the backend or run migrate.py to apply it.\nSaving shipping information does not change payment, delivery status or inventory.\nThis section supersedes the earlier statement that tracking numbers are unavailable.\n'
    return output


def prepare_spec(spec):
    result=spec.model_copy(deep=True);result.source_generation_strategy='RAZORPAY_TEST';result.generation_mode='MODEL'
    paths=['/api/razorpay/orders/{order_id}/'+a for a in ('checkout','verify','reconcile')]
    paths += ['/api/admin/razorpay/orders/{order_id}/'+a for a in ('reconcile','refund','retry-refund')]
    result.api_endpoints=orders.prepare_spec(base_spec(spec)).api_endpoints+[
        APIEndpointDef(endpoint_id='razorpay-'+str(i),method='POST',path=p,description='Test provider only; server authority',auth_required=True) for i,p in enumerate(paths)]
    result.api_endpoints.append(APIEndpointDef(endpoint_id='razorpay-webhook',method='POST',path='/api/razorpay/webhook',description='Raw-body provider HMAC authenticated webhook',auth_required=False))
    result.api_endpoints.append(APIEndpointDef(endpoint_id='manual-delivery',method='POST',path='/api/admin/orders/{order_id}/fulfillment',description='Administrator-only manual demo delivery status',auth_required=True))
    result.api_endpoints.append(APIEndpointDef(endpoint_id='shipping-details',method='POST',path='/api/admin/orders/{order_id}/shipping-details',description='Administrator-only manual courier and tracking details with optimistic version',auth_required=True))
    result.files_to_create=[TargetFileDef(file_path=p,description='Reviewed Razorpay test: '+p,target_module='backend' if p.startswith('backend/') else 'frontend',is_test_file='/tests/' in p,traceable_requirements=[r.id for r in result.requirements]) for p in sources(result)]
    return result
