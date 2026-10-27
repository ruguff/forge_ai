"""Trusted framework glue with real model-generated endpoint bodies.

The scaffold owns FastAPI dependency injection and contract status codes.
The model still generates each endpoint's business logic; no handler fallback.
"""
import ast
import builtins
import json
import keyword
import re
import textwrap


def identifier(value):
    if not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', value) or keyword.iskeyword(value):
        raise ValueError(f'Unsupported Python identifier: {value}')
    return value


def build_module(spec, model, declarative=False):
    if not spec.database_entities or not spec.api_endpoints:
        raise ValueError('Local backend scaffold requires declared entities and API endpoints.')
    definitions = []
    types = {'int':'Integer', 'integer':'Integer', 'string':'String', 'str':'String', 'text':'Text',
             'float':'Float', 'number':'Float', 'bool':'Boolean', 'boolean':'Boolean', 'datetime':'DateTime'}
    for entity in spec.database_entities:
        if entity.relationships:
            raise ValueError('Relationship scaffolding requires an extended runtime; do not silently omit it.')
        name = identifier(entity.entity_name)
        if not any(field.is_primary_key for field in entity.fields):
            raise ValueError(f'{name} requires a declared primary key.')
        lines = [f'class {name}(Base):', f'    __tablename__ = {entity.table_name!r}']
        for field in entity.fields:
            field_name = identifier(field.name)
            data_type = types.get(field.data_type.lower())
            if not data_type:
                raise ValueError(f'Unsupported local field type: {field.data_type}')
            options = f'primary_key={field.is_primary_key}, nullable={field.is_nullable}, unique={field.is_unique}'
            if field.default_value is not None:
                # String defaults are SQL literals, not raw SQL expressions.
                options += f', server_default={str(field.default_value)!r}'
            lines.append(f'    {field_name} = Column({data_type}, {options})')
        definitions.append('\n'.join(lines))
    contracts = []
    for index, endpoint in enumerate(spec.api_endpoints):
        if endpoint.auth_required:
            raise ValueError('Authenticated local backends require an extended scaffold; no auth bypass is generated.')
        if endpoint.method not in ('GET', 'POST', 'PUT', 'PATCH', 'DELETE'):
            raise ValueError('Unsupported local HTTP method')
        parameters = re.findall(r'\{([^}]+)\}', endpoint.path)
        for parameter in parameters:
            identifier(parameter)
        entity = next((e for e in spec.database_entities if e.table_name.lower() in endpoint.path.lower()), spec.database_entities[0])
        # Contract statuses can use concrete IDs while endpoint paths have parameters.
        from app.execution.agent.source_review import same_path
        statuses = [c['status'] for c in spec.acceptance_checks if c.get('method') == endpoint.method
                    and same_path(endpoint.path, c.get('path','')) and 200 <= c.get('status',0) < 300]
        contracts.append({'id': endpoint.endpoint_id, 'method': endpoint.method, 'path': endpoint.path,
            'description': endpoint.description, 'entity': entity.entity_name,
            'parameters': parameters, 'status': statuses[0] if statuses else 200, 'index': index})
    handlers = {}
    for contract in contracts:
        if declarative:
            if contract['method']=='GET':
                body = ('row = db.get(Model, item_id)\nif row is None:\n    raise HTTPException(404, "Not found")\nreturn row'
                        if contract['parameters'] else 'return db.query(Model).all()')
            elif contract['method']=='POST':
                body = 'row = Model(**payload)\ndb.add(row)\ndb.commit()\ndb.refresh(row)\nreturn row'
            else:
                body = 'row = db.get(Model, item_id)\nif row is None:\n    raise HTTPException(404, "Not found")\n'
                body += ('db.delete(row)\ndb.commit()\nreturn None' if contract['method']=='DELETE' else
                    'for name, value in payload.items():\n    setattr(row, name, value)\ndb.commit()\ndb.refresh(row)\nreturn row')
            handlers[contract['id']] = body
            continue
        line_schema = {'type':'object', 'properties':{'lines':{'type':'array','minItems':1,
            'items':{'type':'string','pattern':r'^[^;\r\n]+$'}}}, 'required':['lines'], 'additionalProperties':False}
        body_prompt = '''Generate ONE synchronous Python business function body as JSON {"lines": ["one Python line", ...]}.
Each array entry is one line; indent lines inside if/for blocks with four spaces. Never use semicolons, function headers, decorators or imports.
Available bindings: db (SQLAlchemy Session), payload (validated dict or None), Model (ORM entity class), item_id (path ID or None), HTTPException.
For a create operation instantiate Model(**payload), db.add(record), db.commit(), db.refresh(record), return record.
For update fetch db.get(Model, item_id) once, raise HTTPException(404, 'Not found') if missing, assign payload fields, commit, refresh and return record.
For delete fetch once, raise HTTPException if missing, db.delete(record), db.commit(), return None.
For list return db.query(Model).all(). The session has add/delete/commit methods; an ORM record has no add method.
Implement exactly the endpoint's requirements. Do not invent behavior. Do not close the supplied db.
''' + json.dumps({'endpoint':contract, 'requirements':[{'id':r.id,'description':r.description,'source':r.source.value} for r in spec.requirements],
                 'constraints':spec.constraints, 'entity':next(e.model_dump(mode='json') for e in spec.database_entities if e.entity_name==contract['entity'])})
        body_prompt += '\n```json\n' + json.dumps(line_schema) + '\n```'
        error = ''
        for retry in range(2):
            try:
                reply = json.loads(model.generate_sync(body_prompt + error, output_tokens=768))
                body = textwrap.dedent('\n'.join(reply['lines'])).strip()
                parsed = ast.parse(body)
                # Accept a single function wrapper as output formatting; preserve
                # its statements but use the platform's declared signature.
                if len(parsed.body) == 1 and isinstance(parsed.body[0], ast.FunctionDef):
                    parsed = ast.Module(body=parsed.body[0].body, type_ignores=[])
                    body = ast.unparse(parsed)
                calls = {(node.func.value.id, node.func.attr) for node in ast.walk(parsed)
                    if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name)}
                needed = ({('db','add'),('db','commit')} if contract['method']=='POST' else
                          {('db','delete'),('db','commit')} if contract['method']=='DELETE' else
                          {('db','commit')} if contract['method'] in ('PUT','PATCH') else set())
                if not needed.issubset(calls):
                    raise ValueError(f'The declared mutation requires session operations {sorted(needed)}. ORM records have no add method.')
                if contract['method']=='GET' and not any(owner=='db' and method in ('query','get','execute','scalar','scalars') for owner,method in calls):
                    raise ValueError('A declared data-read endpoint must read actual database records, not return a fabricated list.')
                if ('db','update') in calls:
                    raise ValueError('A SQLAlchemy session has no update method; fetch a record and assign its attributes.')
                validate_body(parsed, contract, spec)
                handlers[contract['id']] = body
                break
            except (ValueError, SyntaxError, KeyError, TypeError) as exc:
                if retry == 1:
                    raise
                error = f'\nFix this failure: {exc}. Return separate Python lines with correct indentation and db session operations.\n'
    operations, routes = [], []
    for contract in contracts:
        parameters = contract['parameters']
        args = ', '.join(['db', 'payload', 'Model'] + parameters)
        alias = f'    item_id = {parameters[0] if parameters else "None"}'
        operations.append(f'def _operation_{contract["index"]}({args}):\n{alias}\n' + textwrap.indent(handlers[contract['id']], '    '))
        signature = [f'{p}: int' for p in parameters]
        mutates = contract['method'] in ('POST','PUT','PATCH')
        if mutates:
            signature.append('payload: dict = Body(...)')
        signature.append('db: Session = Depends(_get_db)')
        callargs = ', '.join(['db', 'payload' if mutates else 'None', contract['entity']] + parameters)
        validation = (f'    _validate_payload(payload, {contract["entity"]}, partial={contract["method"] != "POST"})\n' if mutates else '')
        routes.append(f'@app.{contract["method"].lower()}({contract["path"]!r}, status_code={contract["status"]})\n'
            f'def endpoint_{contract["index"]}({", ".join(signature)}):\n{validation}'
            f'    return _serialize(_operation_{contract["index"]}({callargs}))')
    header = HEADER.replace('endpoint business bodies generated by the configured local model', 'CRUD implementation compiled from the validated model-designed specification') if declarative else HEADER
    source = header + '\n\n'.join(definitions) + '\n\nBase.metadata.create_all(engine)\n\n' + HELPERS + '\n\n'.join(operations + routes) + '\n'
    compile(source, 'backend/app/main.py', 'exec')  # Parse only; never execute on host.
    return source


def validate_body(parsed, contract, spec):
    if not any(isinstance(node, ast.Return) for node in parsed.body):
        raise ValueError('Each handler body must return a result or None.')
    if any(isinstance(node, (ast.Import, ast.ImportFrom, ast.FunctionDef, ast.ClassDef)) for node in parsed.body):
        raise ValueError('Business bodies cannot contain imports or declarations.')
    bindings = {node.id for node in ast.walk(parsed) if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store)}
    bindings |= {node.name for node in ast.walk(parsed) if isinstance(node, ast.ExceptHandler) and node.name}
    bindings |= {node.arg for node in ast.walk(parsed) if isinstance(node, ast.arg)}
    allowed = (set(dir(builtins)) - {'eval','exec','__import__','open','compile'}) | bindings | set(contract['parameters']) | {
        'db','payload','Model','item_id','HTTPException','datetime'} | {entity.entity_name for entity in spec.database_entities}
    unknown = {node.id for node in ast.walk(parsed) if isinstance(node, ast.Name)
               and isinstance(node.ctx, ast.Load) and node.id not in allowed}
    if unknown:
        raise ValueError(f'Unknown handler bindings {sorted(unknown)}. Use db, payload, Model and item_id.')


HEADER = '''# Trusted runtime scaffolding; endpoint business bodies generated by the configured local model.
from pathlib import Path
from datetime import datetime
import os
from fastapi import FastAPI, Body, Depends, HTTPException
from sqlalchemy import create_engine, Column, Integer, String, Text, Float, Boolean, DateTime, text
from sqlalchemy.orm import declarative_base, sessionmaker, Session

app = FastAPI()
database_path = os.environ.get('PROJECTFORGE_DATABASE_PATH', str(Path(__file__).resolve().parents[1] / 'notes.db'))
engine = create_engine('sqlite:///' + database_path, connect_args={'check_same_thread': False})
Base = declarative_base()
SessionLocal = sessionmaker(bind=engine)

'''
HELPERS = '''def _get_db():
    with SessionLocal() as db:
        yield db

def _serialize(value):
    if isinstance(value, Base):
        return {column.name: getattr(value, column.name) for column in value.__table__.columns}
    if isinstance(value, list):
        return [_serialize(item) for item in value]
    if isinstance(value, dict):
        return {key: _serialize(item) for key, item in value.items()}
    return value

def _validate_payload(payload, Model, partial=False):
    fields = {column.name: column for column in Model.__table__.columns if not column.primary_key}
    if not payload or set(payload) - set(fields):
        raise HTTPException(422, 'Provide valid fields for this operation')
    for name, column in fields.items():
        if name not in payload:
            if not partial and not column.nullable and column.default is None and column.server_default is None:
                raise HTTPException(422, f'{name} is required')
            continue
        value = payload[name]
        if value is None and not column.nullable:
            raise HTTPException(422, f'{name} is required')
        if isinstance(column.type, (String, Text)) and (not isinstance(value, str) or not value.strip()):
            raise HTTPException(422, f'{name} must be a nonempty string')
        if isinstance(column.type, DateTime) and isinstance(value, str):
            try:
                payload[name] = datetime.fromisoformat(value)
            except ValueError:
                raise HTTPException(422, f'{name} must be an ISO datetime')

'''
