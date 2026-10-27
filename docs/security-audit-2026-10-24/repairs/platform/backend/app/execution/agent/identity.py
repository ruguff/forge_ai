"""Reviewed catalogue plus customer identity and authorized administration."""
import json
from pathlib import Path
from app.execution.agent import catalogue
from app.execution.agent.identity_runtime import MIGRATION
from app.execution.spec.build_spec_models import TargetFileDef

IDENTITY_ROUTES=(('GET','/api/auth/csrf',False),('POST','/api/auth/register',False),
 ('POST','/api/auth/login',False),('POST','/api/auth/logout',False),
 ('POST','/api/auth/forgot-password',False),('POST','/api/auth/reset-password',False),
 ('GET','/api/account',True),('PATCH','/api/account',True),('POST','/api/account/password',True),
 ('GET','/api/account/addresses',True),('POST','/api/account/addresses',True),
 ('PUT','/api/account/addresses/{address_id}',True),('DELETE','/api/account/addresses/{address_id}',True),
 ('GET','/api/admin/products',True),('POST','/api/admin/products',True),
 ('PUT','/api/admin/products/{product_id}',True),('DELETE','/api/admin/products/{product_id}',True),
 ('PUT','/api/admin/variants/{sku}/stock',True),('GET','/api/admin/categories',True),
 ('POST','/api/admin/categories',True),('PUT','/api/admin/categories/{category_id}',True),('GET','/api/admin/audit',True))

def validate_scope(spec):
    if spec.order_contract or spec.identity_contract is None or spec.catalogue_contract is None or spec.commerce_contract or spec.relational_contract:
        raise ValueError('IDENTITY requires catalogue and identity contracts; orders/payments are not implemented')
    if spec.tech_stack.auth_provider.lower() not in ('session','server-side sessions'):
        raise ValueError('IDENTITY requires reviewed server-side sessions')
    base=spec.model_copy(deep=True);base.identity_contract=None;base.tech_stack.auth_provider='none';base.requirements=[]
    # Identity routes are platform-owned, never supplied by model-written code.
    from app.execution.spec.build_spec_models import APIEndpointDef
    base.api_endpoints=[APIEndpointDef(endpoint_id='catalogue-'+str(i),method='GET',path=path,description=desc,auth_required=False) for i,(path,desc) in enumerate(catalogue.ROUTES)]
    catalogue.validate_scope(base)
    for item in spec.requirements:
        if item.source.value=='USER' and item.dimension in ('functional','functional_requirements'):
            if any(word in item.description.lower() for word in ('checkout','payment','refund','shopping cart','subscription','marketplace','upload')):
                raise ValueError('Requirement exceeds catalogue/identity phase: '+item.id)

def sources(spec):
    validate_scope(spec)
    base=spec.model_copy(deep=True);base.identity_contract=None;base.tech_stack.auth_provider='none';base.requirements=[]
    from app.execution.spec.build_spec_models import APIEndpointDef
    base.api_endpoints=[APIEndpointDef(endpoint_id='catalogue-'+str(i),method='GET',path=path,description=desc,auth_required=False) for i,(path,desc) in enumerate(catalogue.ROUTES)]
    output=catalogue.sources(base);root=Path(__file__).parent
    for name in ('identity_runtime.py','identity_models.py'):
        output['backend/app/'+name]=(root/name).read_text(encoding='utf-8')
    models=(root.parent/'spec/catalogue_contract.py').read_text(encoding='utf-8')
    models=models.replace('from app.execution.spec.commerce_contract import StrictContract',"from pydantic import BaseModel, ConfigDict\nclass StrictContract(BaseModel):\n    model_config=ConfigDict(extra='forbid')")
    output['backend/app/catalogue_models.py']=models
    contract=(root.parent/'spec/identity_contract.py').read_text(encoding='utf-8')
    output['backend/app/identity_contract.py']=contract.replace('from app.execution.spec.commerce_contract import StrictContract',"from pydantic import BaseModel, ConfigDict\nclass StrictContract(BaseModel):\n    model_config=ConfigDict(extra='forbid')")
    output['backend/app/identity.json']=spec.identity_contract.model_dump_json(indent=2)
    output['backend/migrations/0002.json']=json.dumps(MIGRATION,indent=2)
    output['backend/app/main.py']='from .identity_runtime import create_app\napp=create_app()\n'
    output['backend/tests/test_app.py']=output['backend/tests/test_app.py'].replace('TestClient(app)',"TestClient(app,client=('127.0.0.1',50000))")
    output['backend/migrate.py']='''import asyncio
from app.main import app
async def main():
    async with app.router.lifespan_context(app):
        print('Catalogue and identity migrations are current')
asyncio.run(main())
'''
    output['backend/manage.py']='''"""Explicit server operator action; no default administrator credentials."""
import argparse,asyncio,getpass,os
from app.main import app
from app.identity_runtime import create_admin
parser=argparse.ArgumentParser()
parser.add_argument('command',choices=['create-admin'])
parser.add_argument('--email',required=True)
parser.add_argument('--name',default='Administrator')
parser.add_argument('--password-env',help='Environment variable for synthetic automation only; otherwise prompts securely')
args=parser.parse_args()
password=os.environ.pop(args.password_env) if args.password_env else getpass.getpass('Admin passphrase (15+ characters): ')
async def main():
    async with app.router.lifespan_context(app):
        create_admin(app.state.engine,app.state.identity_metadata,args.email,password,args.name)
        print('Administrator created; no existing customer was promoted')
asyncio.run(main())
'''
    from app.execution.spec.identity_ui import ui_manifest
    identity_ui=ui_manifest()
    component=(root/'identity_templates/Identity.tsx').read_text(encoding='utf-8')
    component="import uiContract from './ui-contract.json';\nconst identityIds=uiContract.identity.ids;\n"+component
    for key,value in identity_ui['ids'].items():
        component=component.replace('data-testid="'+value+'"','data-testid={identityIds.'+key+'}')
    output['frontend/src/Identity.tsx']=component
    output['frontend/src/identity.css']=(root/'identity_templates/identity.css').read_text(encoding='utf-8')
    app=output['frontend/src/App.tsx']
    app="import Identity from './Identity';\n"+app
    app=app.replace(' return <>\n'," if(path.startsWith('/account')||path==='/admin')return <Identity/>;\n return <>\n",1)
    app=app.replace('<a href="#approach">Our approach</a>','<a href="/account">My account</a><a href="/admin">Administration</a>')
    output['frontend/src/App.tsx']=app
    ui=json.loads(output['frontend/src/ui-contract.json']);ui['identity']=identity_ui
    output['frontend/src/ui-contract.json']=json.dumps(ui,indent=2)
    output['README.md']+=README
    return output

def prepare_spec(spec):
    result=spec.model_copy(deep=True);result.source_generation_strategy='IDENTITY';result.generation_mode='MODEL'
    from app.execution.spec.build_spec_models import APIEndpointDef
    result.api_endpoints=[APIEndpointDef(endpoint_id='module-'+str(i),method=method,path=path,description='Reviewed module operation',auth_required=auth)
        for i,(method,path,auth) in enumerate([('GET',path,False) for path,_ in catalogue.ROUTES]+list(IDENTITY_ROUTES))]
    generated=sources(result)
    result.files_to_create=[TargetFileDef(file_path=path,description='Reviewed identity module: '+path,target_module='backend' if path.startswith('backend/') else 'frontend',is_test_file='/tests/' in path,traceable_requirements=[r.id for r in result.requirements]) for path in generated]
    return result

README='''
## Accounts and administration
Set `backend/app/identity.json` public_origin to the exact browser origin.
HTTPS and Secure HttpOnly cookies are required by default. For local demonstrations
only, explicitly enable allow_local_http with http://127.0.0.1:3001.
Run backend with `uvicorn app.main:app --host 127.0.0.1 --port 8001 --no-proxy-headers`.
The generated Vite proxy uses port 8001; change its target if necessary.
Run `python migrate.py` then `python manage.py create-admin --email you@example.com`.
No administrator password is supplied. Existing customers cannot be promoted by this command.
Visit /account for registration, login, profile, password recovery and owned addresses.
Visit /admin for authorized catalogue/stock operations. Prices are integer minor units.
Version conflicts require reload; they are never silently overwritten.
Local recovery uses a server-only temporary mail outbox; its directory can be set with
IDENTITY_OUTBOX_DIR outside the served source tree. Read the JSON recovery_url as the
local operator; there is no public token lookup. Protect that directory with OS permissions.
For HTTPS deployments configure IDENTITY_MAIL_MODE=smtp, IDENTITY_MAIL_FROM,
IDENTITY_SMTP_HOST/PORT/USER/PASSWORD on the server. Real delivery is not verified here.
Passwords, reset tokens and session cookies must never enter logs or source control.
Do not deploy without TLS, trusted reverse-proxy configuration, backups, dependency
review and an independent security review. Orders, cart and payments are not implemented.
'''
