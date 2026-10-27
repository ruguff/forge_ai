import json,shutil
from pathlib import Path
root=Path(__file__).resolve().parents[1]
source=root/'backend/app/execution/agent'
ids={'status':'delivery-status','details':'shipping-details','form':'shipping-form','track':'track-shipment',
     'page':'shipment-page','summary':'shipment-summary','timeline':'shipment-timeline','number':'shipment-number','empty':'shipment-empty'}
ui={'version':3,'mode':'manual','ids':ids}
route=" if(path.match(/^\\/orders\\/[^/]+\\/tracking\\/?$/))return <ShipmentTracking key={path} orderId={path.split('/')[2]}/>;\n"
note='''
## Customer shipment tracking
Customers can select Track shipment from their own order history to open
/orders/{order_id}/tracking. The page shows store-recorded delivery milestones,
courier name, tracking number, copy and refresh controls. Cancelled, expired,
refunded, unpaid and held orders have distinct messages. No delivery estimate,
live location or automatic carrier update is invented.
The owner-only GET /api/orders/{order_id}/shipment returns a limited projection
of the order and delivery audit timestamps. It exposes no admin actor or address
information. Existing orders and migrations are preserved; no new schema is needed.
Restart the backend and refresh the frontend to activate this feature.
'''
for name in ('payments.py','razorpay.py'):
    path=source/name;content=path.read_text(encoding='utf-8')
    if "endpoint_id='customer-shipment'" in content:continue
    marker="root = Path(__file__).parent"
    assert marker in content
    addition="\n    output['frontend/src/identity.css'] += (root/'order_templates/shipment.css').read_text(encoding='utf-8')\n    output['frontend/src/App.tsx'] = \"import {ShipmentTracking} from './Fulfillment';\\n\" + output['frontend/src/App.tsx']\n    output['frontend/src/App.tsx'] = output['frontend/src/App.tsx'].replace(\" if(path==='/cart'\", "+repr(route)+"+\" if(path==='/cart'\")"
    content=content.replace(marker,marker+addition)
    lines=content.splitlines()
    for index,line in enumerate(lines):
        if "ui['delivery'] =" in line:lines[index]="    ui['delivery'] = "+repr(ui)
    content='\n'.join(lines)+'\n'
    content=content.replace('    result.files_to_create',"    result.api_endpoints.append(APIEndpointDef(endpoint_id='customer-shipment',method='GET',path='/api/orders/{order_id}/shipment',description='Owner-only shipment status, courier and recorded milestones',auth_required=True))\n    result.files_to_create")
    content=content.replace('    return output',"    output['README.md'] += "+repr(note)+"\n    return output")
    path.write_text(content,encoding='utf-8')
for name in ('payments-app','razorpay-app'):
    demo=root/'docs/ecommerce-evidence'/name
    shutil.copyfile(source/'fulfillment_runtime.py',demo/'backend/app/fulfillment_runtime.py')
    shutil.copyfile(source/'order_templates/Fulfillment.tsx',demo/'frontend/src/Fulfillment.tsx')
    path=demo/'frontend/src/App.tsx';content=path.read_text(encoding='utf-8')
    content="import {ShipmentTracking} from './Fulfillment';\n"+content
    path.write_text(content.replace(" if(path==='/cart'",route+" if(path==='/cart'"),encoding='utf-8')
    path=demo/'frontend/src/identity.css';path.write_text(path.read_text(encoding='utf-8')+'\n'+(source/'order_templates/shipment.css').read_text(encoding='utf-8'),encoding='utf-8')
    path=demo/'frontend/src/ui-contract.json';data=json.loads(path.read_text(encoding='utf-8'));data['delivery']=ui;path.write_text(json.dumps(data,indent=2),encoding='utf-8')
    path=demo/'README.md';path.write_text(path.read_text(encoding='utf-8')+note,encoding='utf-8')
for name in ('test_payments_compiler.py','test_razorpay_compiler.py'):
    path=root/'backend/tests'/name;content=path.read_text(encoding='utf-8')
    content=content.replace("['delivery']['version']==2", "['delivery']['version']==3")
    anchor="    assert 'frontend/src/Fulfillment.tsx' in after"
    content=content.replace(anchor,anchor+"\n    assert any(e.path=='/api/orders/{order_id}/shipment' and e.auth_required for e in prepare_spec(spec()).api_endpoints)\n    assert 'ShipmentTracking' in after['frontend/src/App.tsx']\n    assert '.shipment-timeline' in after['frontend/src/identity.css']")
    path.write_text(content,encoding='utf-8')
