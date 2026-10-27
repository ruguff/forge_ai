"""Bounded multi-entity source compiler; independent from legacy CRUD strategy."""
import json
import keyword
import re
from pathlib import Path
from app.execution.spec.build_spec_models import APIEndpointDef, UIContract
from app.execution.agent import declarative


def schema_for(spec):
    if spec.order_contract or spec.identity_contract or spec.commerce_contract or spec.catalogue_contract or not spec.relational_contract:
        raise ValueError('RELATIONAL_CRUD requires a relational contract and cannot implement commerce rules')
    if spec.project_type.value != 'FULLSTACK_WEB':
        raise ValueError('Relational generator currently requires FULLSTACK_WEB')
    if 'fastapi' not in spec.tech_stack.backend_framework.lower() or 'react' not in spec.tech_stack.frontend_framework.lower():
        raise ValueError('Relational runtime requires FastAPI and React')
    if spec.tech_stack.frontend_styling.lower() not in ('css','plain css','none'):
        raise ValueError('Relational foundation currently uses plain CSS; other styling systems are not silently substituted')
    if spec.tech_stack.primary_database.lower() not in ('sqlite', 'postgresql'):
        raise ValueError('Relational storage must be SQLite or PostgreSQL')
    if spec.tech_stack.auth_provider.lower() not in ('none','no authentication'):
        raise ValueError('Authentication is not implemented by the relational foundation')
    if not 2 <= len(spec.database_entities) <= 12:
        raise ValueError('Relational CRUD supports 2–12 entities')
    tables = {}
    names = set()
    for entity in spec.database_entities:
        for name in [entity.table_name, entity.entity_name] + [f.name for f in entity.fields]:
            if not re.fullmatch(r'[A-Za-z][A-Za-z0-9_]{0,47}', name) or keyword.iskeyword(name):
                raise ValueError('Invalid relational identifier: '+name)
        if (entity.table_name.lower().startswith('projectforge_') or entity.table_name.lower() in {t.lower() for t in tables}
                or entity.entity_name.lower() in names):
            raise ValueError('Duplicate or reserved entity name')
        names.add(entity.entity_name.lower())
        fields = {f.name:f for f in entity.fields}
        if len(fields) != len(entity.fields) or not 2 <= len(fields) <= 24:
            raise ValueError('Entity fields must be unique and bounded')
        if entity.relationships:
            raise ValueError('Use typed relational_contract relationships, not ambiguous text')
        keys = [f for f in entity.fields if f.is_primary_key]
        if len(keys) != 1 or keys[0].data_type != 'integer' or keys[0].is_nullable:
            raise ValueError('Each entity needs one nonnullable integer primary key')
        if any(f.data_type not in ('integer','text','string') or f.default_value is not None for f in entity.fields):
            raise ValueError('Only integer/text fields without implicit defaults are supported')
        tables[entity.table_name] = fields
    refs = set()
    for ref in spec.relational_contract.relationships:
        source = tables.get(ref.source_table, {}).get(ref.source_column)
        target = tables.get(ref.target_table, {}).get(ref.target_column)
        if source is None or target is None or source.data_type != target.data_type:
            raise ValueError('Relationship must reference existing compatible fields')
        if source.is_primary_key or not (target.is_primary_key or target.is_unique):
            raise ValueError('Relationship target must be a unique key; source must not be the primary key')
        if ref.on_delete == 'SET NULL' and not source.is_nullable:
            raise ValueError('SET NULL requires a nullable field')
        key = (ref.source_table,ref.source_column)
        if key in refs:
            raise ValueError('Duplicate foreign key declaration')
        refs.add(key)
    expected = {(method, path) for table in tables for method,path in [
        ('GET','/api/'+table),('POST','/api/'+table),('PUT','/api/'+table+'/{record_id}'),('DELETE','/api/'+table+'/{record_id}')]}
    if any(e.auth_required for e in spec.api_endpoints) or {(e.method,e.path) for e in spec.api_endpoints} != expected or len(spec.api_endpoints) != len(expected):
        raise ValueError('Relational CRUD requires exact unauthenticated canonical CRUD routes; custom operations are unsupported')
    for requirement in spec.requirements:
        if requirement.source.value == 'USER' and requirement.dimension in ('functional','functional_requirements'):
            if any(word in requirement.description.lower() for word in ('payment','checkout','login','authentication','reservation','upload','refund')):
                raise ValueError('Requested business functionality is outside RELATIONAL_CRUD: '+requirement.id)
    return {'title':spec.project_name, 'revision':'0001', 'database':spec.tech_stack.primary_database.lower(), 'entities':[e.model_dump() for e in spec.database_entities],
            'relationships':[r.model_dump() for r in spec.relational_contract.relationships]}


def entity_spec(spec, entity):
    single = spec.model_copy(deep=True)
    single.relational_contract = None
    single.database_entities = [entity]
    single.requirements = []  # Parent scope is checked before reusing UI scaffolding.
    single.api_endpoints = [e for e in spec.api_endpoints if e.path in ('/api/'+entity.table_name, '/api/'+entity.table_name+'/{record_id}')]
    single.ui_contract = UIContract(namespace=entity.table_name.lower().replace('_','-'))
    return single


def sources(spec):
    schema = schema_for(spec)
    first = entity_spec(spec, spec.database_entities[0])
    common = ['backend/app/__init__.py','frontend/package.json','frontend/tsconfig.json','frontend/vite.config.ts',
              'frontend/src/main.tsx','frontend/index.html']
    output = {name:declarative.file_source(first,name) for name in common}
    output['backend/app/relational_runtime.py'] = Path(__file__).with_name('relational_runtime.py').read_text(encoding='utf-8')
    output['backend/app/schema.json'] = json.dumps(schema,indent=2)
    output['backend/app/main.py'] = 'from .relational_runtime import create_app\napp = create_app()\n'
    output['backend/requirements.txt'] = 'fastapi>=0.115,<1\nuvicorn>=0.30,<1\nsqlalchemy>=2,<3\npydantic>=2,<3\npsycopg[binary]>=3.2,<4\n'
    output['backend/tests/test_schema.py'] = '''from fastapi.testclient import TestClient
from app.main import app

def test_api_schema_available():
    with TestClient(app) as client:
        response = client.get('/openapi.json')
        assert response.status_code == 200
        assert response.json()['paths']
'''
    output['backend/migrations/0001.json'] = json.dumps(schema,indent=2)
    output['backend/compose.yaml'] = '''services:
  db:
    image: postgres:15-bookworm
    environment:
      POSTGRES_USER: projectforge
      POSTGRES_DB: generated_app
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:?Set a local development database password}
    ports:
      - "127.0.0.1:5432:5432"
    volumes:
      - database:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U projectforge -d generated_app"]
      interval: 5s
      timeout: 3s
      retries: 10
volumes:
  database:
'''
    output['backend/migrate.py'] = ('from app.relational_runtime import create_app, migrate, make_metadata\nimport json\nfrom pathlib import Path\n'
        'app = create_app()\nschema = json.loads(Path("app/schema.json").read_text())\n'
        'migrate(app.state.engine, schema, make_metadata(schema))\nprint("Migration 0001 applied or already current")\n')
    imports, options = [], []
    for index, entity in enumerate(spec.database_entities):
        name = 'Entity'+str(index)
        output['frontend/src/'+name+'.tsx'] = declarative.file_source(entity_spec(spec, entity),'frontend/src/App.tsx').replace('Local data, saved on this device.','Records saved in the configured database.')
        imports.append(f"import {name} from './{name}';")
        options.append('{label:'+json.dumps(entity.entity_name)+',View:'+name+'}')
    output['frontend/src/App.tsx'] = "import {useState} from 'react';\n"+'\n'.join(imports)+'''
const views = ['''+','.join(options)+'''];
export default function App(){const [selected,setSelected]=useState(0);const View=views[selected].View;
return <><nav aria-label="Entities" style={{display:'flex',gap:12,flexWrap:'wrap',padding:20}}>{views.map((v,i)=><button key={v.label} aria-pressed={i===selected} onClick={()=>setSelected(i)}>{v.label}</button>)}</nav><View key={selected}/></>;}
'''
    output['README.md'] = '''# Relational CRUD development application

This is a related-data foundation, not an authenticated store. Bind locally only.
No payment, inventory reservation or commerce permissions are implemented.

Backend: create a virtual environment and install backend/requirements.txt.
From backend set POSTGRES_PASSWORD locally, then docker compose up -d --wait.
This development database uses a persistent named volume and binds only to localhost.
Set DATABASE_URL to postgresql+psycopg://USER:PASSWORD@127.0.0.1:5432/DATABASE.
Use USER=projectforge and DATABASE=generated_app with the supplied compose file.
URL-encode special characters in the password. Never commit passwords or .env files.
SQLite builds use sqlite:///development.db. Regenerate an explicitly SQLite spec
for that provider; the runtime refuses silent provider substitution.
From backend run python migrate.py, then python -m uvicorn app.main:app --host 127.0.0.1 --port 8001.
Frontend: from frontend run npm install --ignore-scripts and npm run dev.

Migration 0001 is immutable and checksum-checked. Existing unversioned tables or
changed schemas fail closed; there is no destructive reset or automatic migration.
The initial migration manifest is backend/migrations/0001.json. Runtime uses the
identical schema in app/schema.json. Keep both versioned with source control.
API lists are limited to 100 rows by default (maximum 200) with limit/offset.
The initial UI displays the first page only. Database credentials stay server-side.
'''
    return output


def prepare_spec(spec):
    """Normalize only the source manifest; never change acceptance assertions."""
    from app.execution.spec.build_spec_models import TargetFileDef
    result = spec.model_copy(deep=True)
    result.source_generation_strategy = 'RELATIONAL_CRUD'
    result.generation_mode = 'MODEL'
    generated = sources(result)
    result.files_to_create = [TargetFileDef(file_path=path, description='Reviewed relational module: '+path,
        target_module='backend' if path.startswith('backend/') else 'frontend', is_test_file='/tests/' in path,
        dependencies=[], traceable_requirements=[r.id for r in result.requirements]) for path in generated]
    return result
