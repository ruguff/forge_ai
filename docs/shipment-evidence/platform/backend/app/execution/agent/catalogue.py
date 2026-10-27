"""Reviewed public catalogue generator. No model-written business code or secrets."""
import json
from pathlib import Path
from app.execution.agent import declarative
from app.execution.agent.catalogue_assets import SHAPES, svg
from app.execution.spec.catalogue_ui import ui_manifest
from app.execution.spec.build_spec_models import APIEndpointDef, TargetFileDef

ROUTES = (('/api/store','Store configuration'),('/api/categories','Active categories'),
          ('/api/products','Filtered and paginated catalogue'),('/api/products/{slug}','Product variants and images'))


def validate_scope(spec):
    if spec.order_contract or spec.identity_contract or spec.catalogue_contract is None or spec.commerce_contract or spec.relational_contract:
        raise ValueError('CATALOGUE requires its own typed contract and cannot silently implement full commerce')
    if spec.project_type.value != 'FULLSTACK_WEB' or spec.tech_stack.primary_database.lower() != 'postgresql':
        raise ValueError('Catalogue requires a full-stack PostgreSQL project')
    if 'fastapi' not in spec.tech_stack.backend_framework.lower() or 'react' not in spec.tech_stack.frontend_framework.lower():
        raise ValueError('Catalogue uses React and FastAPI')
    if spec.tech_stack.frontend_styling.lower() not in ('css','plain css') or spec.tech_stack.auth_provider.lower() not in ('none','no authentication'):
        raise ValueError('This catalogue phase uses plain CSS and read-only public operations; identity is a separate phase')
    if spec.database_entities:
        raise ValueError('Catalogue tables are supplied by the reviewed module; custom entities need a later extension')
    if {(e.method,e.path,e.auth_required) for e in spec.api_endpoints} != {('GET',path,False) for path,_ in ROUTES} or len(spec.api_endpoints)!=len(ROUTES):
        raise ValueError('Catalogue supports only the four declared public read routes')
    for requirement in spec.requirements:
        if requirement.source.value == 'USER' and requirement.dimension in ('functional','functional_requirements'):
            value = requirement.description.lower()
            unsupported = ('checkout','payment','refund','login','authentication','user account','shopping cart','upload','subscription','marketplace','admin ')
            if any(term in value for term in unsupported):
                raise ValueError('Requested functionality exceeds the read-only catalogue phase: '+requirement.id)


def sources(spec):
    validate_scope(spec)
    config = spec.catalogue_contract.model_dump(mode='json')
    base = spec.model_copy(deep=True)
    # Reuse reviewed tooling files, never the legacy CRUD behavior.
    base.catalogue_contract = None
    from app.execution.spec.build_spec_models import DatabaseEntityDef, DatabaseFieldDef
    base.database_entities = [DatabaseEntityDef(entity_name='Tooling',table_name='tooling',fields=[
        DatabaseFieldDef(name='id',data_type='integer',is_primary_key=True),DatabaseFieldDef(name='name',data_type='text')])]
    base.api_endpoints = [APIEndpointDef(endpoint_id=method,method=method,path='/api/tooling'+suffix,description='Tooling only',auth_required=False)
        for method,suffix in [('GET',''),('POST',''),('PUT','/{record_id}'),('DELETE','/{record_id}')]]
    base.requirements = []
    common = ('backend/app/__init__.py','frontend/package.json','frontend/tsconfig.json','frontend/src/main.tsx','frontend/index.html')
    output = {path:declarative.file_source(base,path) for path in common}
    output['backend/requirements.txt'] = 'fastapi>=0.115,<1\nuvicorn>=0.30,<1\nsqlalchemy>=2,<3\npydantic>=2,<3\npsycopg[binary]>=3.2,<4\n'
    output['backend/requirements-dev.txt'] = '-r requirements.txt\npytest>=8,<9\nhttpx>=0.27,<1\n'
    root = Path(__file__).parent
    for name in ('catalogue_runtime.py','relational_runtime.py'):
        output['backend/app/'+name] = (root/name).read_text(encoding='utf-8')
    output['backend/app/catalogue.json'] = json.dumps(config,indent=2)
    output['backend/migrations/0001.json'] = json.dumps({'module':'catalogue-v1','database':'postgresql','config':config},indent=2)
    output['backend/app/main.py'] = 'from .catalogue_runtime import create_app\napp = create_app()\n'
    # Migration command deliberately does not require test dependencies.
    output['backend/migrate.py'] = '''import json
from pathlib import Path
from app.main import app
from app.catalogue_runtime import metadata_for, seed_database
from app.relational_runtime import migrate
config = json.loads(Path('app/catalogue.json').read_text(encoding='utf-8'))
schema = json.loads(Path('migrations/0001.json').read_text(encoding='utf-8'))
metadata = metadata_for(config['currency'])
migrate(app.state.engine,schema,metadata)
seed_database(app.state.engine,metadata,config)
print('Catalogue migration and initial seed are current')
'''
    output['backend/tests/test_app.py'] = '''from fastapi.testclient import TestClient
from app.main import app

def test_public_read_contract():
    with TestClient(app) as client:
        assert client.get('/api/store').status_code == 200
        assert client.get('/api/products').status_code == 200
        assert client.post('/api/products',json={}).status_code == 405
'''
    for name in ('App.tsx','styles.css'):
        output['frontend/src/'+name] = (root/'catalogue_templates'/name).read_text(encoding='utf-8')
    output['frontend/src/ui-contract.json'] = json.dumps(ui_manifest(),indent=2)
    tsconfig = json.loads(output['frontend/tsconfig.json'])
    tsconfig['compilerOptions']['resolveJsonModule'] = True
    output['frontend/tsconfig.json'] = json.dumps(tsconfig,indent=2)
    output['frontend/vite.config.ts'] = VITE_CONFIG
    output['frontend/index.html'] = output['frontend/index.html'].replace('<html>','<html lang="en">').replace('<title>Local application</title>','<title>Catalogue</title>')
    for asset in SHAPES:
        output['frontend/public/assets/'+asset+'.svg'] = svg(asset)
    output['backend/compose.yaml'] = COMPOSE
    output['README.md'] = README
    return output


def prepare_spec(spec):
    result = spec.model_copy(deep=True)
    result.source_generation_strategy = 'CATALOGUE'
    result.generation_mode = 'MODEL'
    validate_scope(result)
    generated = sources(result)
    result.files_to_create = [TargetFileDef(file_path=path,description='Reviewed catalogue module: '+path,
        target_module='backend' if path.startswith('backend/') else 'frontend',is_test_file='/tests/' in path,
        traceable_requirements=[r.id for r in result.requirements]) for path in generated]
    return result


COMPOSE = '''services:
  db:
    image: postgres:15-bookworm
    environment:
      POSTGRES_USER: projectforge
      POSTGRES_DB: catalogue
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:?Set a local database password}
    ports:
      - "127.0.0.1:5432:5432"
    volumes:
      - catalogue_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U projectforge -d catalogue"]
      interval: 5s
      timeout: 3s
      retries: 10
volumes:
  catalogue_data:
'''

VITE_CONFIG = '''import {defineConfig, type Plugin} from 'vite';
import react from '@vitejs/plugin-react';
const proxy={'/api':'http://127.0.0.1:8001'};
const safeProductPaths:Plugin={
 name:'catalogue-safe-product-paths',
 configureServer(server){server.middlewares.use((request,_response,next)=>{
  const incoming=request as typeof request & {url?:string};
  if(incoming.url?.startsWith('/products/')){try{decodeURI(incoming.url);}catch{incoming.url='/';}}
  next();
 });},
 configurePreviewServer(server){server.middlewares.use((request,_response,next)=>{
  const incoming=request as typeof request & {url?:string};
  if(incoming.url?.startsWith('/products/')){try{decodeURI(incoming.url);}catch{incoming.url='/';}}
  next();
 });}
};
export default defineConfig({cacheDir:'.vite-cache',plugins:[safeProductPaths,react()],
 server:{host:'127.0.0.1',port:3001,proxy},preview:{host:'127.0.0.1',port:3001,proxy}});
'''

README = '''# Generated catalogue

React/TypeScript + FastAPI + PostgreSQL. This phase is a public, read-only catalogue.
Accounts, administration, carts, checkout and payments are not implemented.

## Local setup

From backend create a virtual environment and install requirements.txt. Supply a
local POSTGRES_PASSWORD and run docker compose up -d --wait. Set DATABASE_URL to
postgresql+psycopg://projectforge:URL_ENCODED_PASSWORD@127.0.0.1:5432/catalogue.
Keep these credentials on the server and out of source control. The supplied
Compose service uses a persistent volume and binds only to localhost.

From backend run python migrate.py, then
python -m uvicorn app.main:app --host 127.0.0.1 --port 8001.
From frontend run npm install --ignore-scripts and npm run dev.
Open http://127.0.0.1:3001. npm run build produces frontend/dist; npm run preview
provides a local built preview with its API proxy. Deployment needs a reverse proxy
serving frontend/dist and routing /api to FastAPI, including SPA route fallback.

## Data and supported behavior

Initial data in backend/app/catalogue.json is validated seed content, not generated
activity or sales. Startup applies immutable migration 0001 and seeds only once.
Repeated startup preserves edits. Changed schemas/config require a reviewed new
migration; the runtime never resets a database to make a build pass. PostgreSQL
constraints protect SKUs, relationships, nonnegative prices and stock, and currency.
Prices use integer minor units. INR, USD, EUR and GBP use two decimal places.

Public routes: GET /api/store, /api/categories, /api/products and /api/products/SLUG.
Products supports q, category, min_price, max_price (minor units), in_stock, sort,
page and limit (1-48). Search includes product name, description and active SKUs;
wildcard characters are literal. Filters apply to the same active variant.
Hidden products, hidden categories and inactive variants are not returned.
Local reviewed SVG illustrations are served from frontend/public/assets. File
uploads and remote image fetching are not supported in this phase.

The frontend uses a shared ui-contract.json for browser selectors, CSS design
tokens, responsive pages and native keyboard controls. No reviews, discount claims,
delivery promises or successful transactions are invented. Stock is a catalogue
snapshot; reservation and overselling protection are a later phase.

## Testing and release limits

Install backend/requirements-dev.txt for local pytest. Independent platform checks
and screenshots are stored outside generated implementation under .projectforge.
Functional, accessibility, security and performance evidence must be reported
separately. Passing catalogue tests does not mean production-ready commerce.
'''
