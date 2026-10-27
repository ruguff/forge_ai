"""Reviewed identity + server-authoritative carts and unpaid orders."""
import json
from pathlib import Path
from app.execution.agent import identity
from app.execution.agent.order_runtime import SCHEMA
from app.execution.spec.build_spec_models import APIEndpointDef,TargetFileDef
ROUTES=(('GET','/api/cart'),('PUT','/api/cart/items/{sku}'),('POST','/api/orders'),('GET','/api/orders'),
        ('GET','/api/orders/{order_id}'),('POST','/api/orders/{order_id}/cancel'),('GET','/api/admin/orders'))
def validate_scope(spec):
    if not spec.order_contract:raise ValueError('ORDERS requires explicit shipping/tax/discount/reservation rules')
    base=spec.model_copy(deep=True);base.order_contract=None;base.requirements=[]
    identity.validate_scope(base)
    for r in spec.requirements:
        if r.source.value=='USER' and r.dimension in ('functional','functional_requirements'):
            if any(t in r.description.lower() for t in ('razorpay','refund','subscription','marketplace','upload','collect payment','paid order','fulfillment')):
                raise ValueError('Requirement exceeds unpaid order phase: '+r.id)
def sources(spec):
    validate_scope(spec);base=spec.model_copy(deep=True);base.order_contract=None;base.requirements=[]
    output=identity.sources(base);root=Path(__file__).parent
    contract=(root.parent/'spec/order_contract.py').read_text(encoding='utf-8').replace('from app.execution.spec.commerce_contract import StrictContract',"StrictContract=Input")
    runtime=(root/'order_runtime.py').read_text(encoding='utf-8').replace('from app.execution.spec.order_contract import OrderContract','')
    runtime=runtime.replace('class CartLine(Input):',contract+'\nclass CartLine(Input):')
    output['backend/app/order_runtime.py']=runtime
    output['backend/app/orders.json']=spec.order_contract.model_dump_json(indent=2)
    output['backend/migrations/0003.json']=json.dumps({**SCHEMA,'rules':spec.order_contract.model_dump(mode='json')},indent=2)
    output['backend/app/main.py']='from .order_runtime import create_app\napp=create_app()\n'
    output['frontend/src/Orders.tsx']=(root/'order_templates/Orders.tsx').read_text(encoding='utf-8')
    output['frontend/src/Identity.tsx']=output['frontend/src/Identity.tsx'].replace('async function api(', 'export async function api(')
    app=output['frontend/src/App.tsx']
    app="import Orders,{AddToCart} from './Orders';\n"+app
    app=app.replace(" if(path.startsWith('/account')", " if(path==='/cart'||path==='/orders'||path==='/admin/orders')return <Orders/>;\n if(path.startsWith('/account')")
    app=app.replace('<a href="/account">My account</a>','<a href="/cart">Cart</a><a href="/orders">Orders</a><a href="/account">My account</a>')
    app=app.replace('<div className="catalogue-notice">','<AddToCart sku={selected.sku}/><div className="catalogue-notice">')
    app=app.replace('Online checkout is not enabled yet.','Create an unpaid order from your cart. Payments are disabled.')
    output['frontend/src/App.tsx']=app
    ui=json.loads(output['frontend/src/ui-contract.json']);ui['orders']={'version':1,'ids':{'add':'order-add','cart':'order-cart','checkout':'order-checkout','history':'order-history','message':'order-message'}}
    output['frontend/src/ui-contract.json']=json.dumps(ui,indent=2)
    output['frontend/src/identity.css']+='\n.order-item{display:flex;gap:16px;justify-content:space-between;flex-wrap:wrap;padding:18px 0;border-bottom:1px solid #d8ded3}.order-item input{max-width:90px}.order-total{font-size:22px;font-weight:600}.order-state{font-size:13px;padding:8px;border-radius:6px;background:#eee9db}.order-actions{display:flex;gap:12px;flex-wrap:wrap;margin:20px 0}\n'
    output['README.md']+='''
## Unpaid orders and inventory reservations
Visit /cart, /orders and /admin/orders. Checkout creates an awaiting_payment order;
it never charges money or marks an order paid/fulfilled. Cart quantities do not hold
stock. Checkout reserves available units atomically; cancellation or expiry restores
them once. Admin stock input means AVAILABLE units, excluding active reservations.
The expiry worker runs every 30 seconds; startup and cart/order operations also sweep.
Rules in orders.json are explicit configuration, not authoritative tax/shipping advice.
Totals use integer minor units; discount rounds down, tax rounds half up on discounted
merchandise, shipping is added afterward. Rules are snapshotted and migration-versioned.
Order history is bounded to the latest 100 orders; pagination is a later improvement.
The UI keeps an unconfirmed request key in sessionStorage (no credentials) for explicit
retry after connection loss. Reuse that key, do not submit a new order to resolve ambiguity.
Reviewed mutations share a PostgreSQL transaction advisory lock; this favors correctness
for a small single store over throughput. Direct database writes bypass application rules.
Payments, fulfillment and refunds remain disabled. Inventory is not production certified.
'''
    return output
def prepare_spec(spec):
    result=spec.model_copy(deep=True);result.source_generation_strategy='ORDERS';result.generation_mode='MODEL'
    result.api_endpoints=identity.prepare_spec(result.model_copy(update={'order_contract':None,'requirements':[]})).api_endpoints
    result.api_endpoints += [APIEndpointDef(endpoint_id='order-'+str(i),method=method,path=path,description='Reviewed unpaid order operation',auth_required=True) for i,(method,path) in enumerate(ROUTES)]
    output=sources(result)
    result.files_to_create=[TargetFileDef(file_path=path,description='Reviewed order module: '+path,target_module='backend' if path.startswith('backend/') else 'frontend',is_test_file='/tests/' in path,traceable_requirements=[r.id for r in result.requirements]) for path in output]
    return result
