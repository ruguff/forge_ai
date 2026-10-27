"""Reviewed relational CRUD runtime copied into generated applications.

Only the compiler writes schema.json. No model-written SQL or Python is evaluated.
Authentication and commerce operations are deliberately outside this module.
"""
import hashlib
import json
import os
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, HTTPException, Query, Response
from pydantic import ConfigDict, StrictInt, StrictStr, create_model, field_validator
from sqlalchemy import (MetaData, Table, Column, Integer, Text, ForeignKey,
                        create_engine, select, event, text)
from sqlalchemy.exc import IntegrityError


def make_metadata(schema):
    metadata = MetaData()
    references = {(r['source_table'], r['source_column']): r for r in schema['relationships']}
    for entity in schema['entities']:
        columns = []
        for field in entity['fields']:
            args = []
            ref = references.get((entity['table_name'], field['name']))
            if ref:
                args.append(ForeignKey(ref['target_table']+'.'+ref['target_column'], ondelete=ref['on_delete']))
            columns.append(Column(field['name'], Integer if field['data_type'] == 'integer' else Text,
                *args, primary_key=field['is_primary_key'], nullable=False if field['is_primary_key'] else field['is_nullable'],
                unique=field['is_unique']))
        Table(entity['table_name'], metadata, *columns)
    return metadata


def migrate(engine, schema, metadata, followups=None):
    """Immutable initial migration. Drift is an error, never an automatic reset."""
    digest = hashlib.sha256(json.dumps(schema, sort_keys=True).encode()).hexdigest()
    with engine.begin() as conn:
        if engine.dialect.name == 'postgresql':
            conn.execute(text('SELECT pg_advisory_xact_lock(681072014)'))
        conn.execute(text('CREATE TABLE IF NOT EXISTS projectforge_migrations (revision VARCHAR(32) PRIMARY KEY, checksum VARCHAR(64) NOT NULL)'))
        existing = conn.execute(text('SELECT revision, checksum FROM projectforge_migrations')).all()
        if existing:
            allowed={'0001':digest,**(followups or {})}
            actual=dict(existing)
            if actual.get('0001')!=digest or any(allowed.get(revision)!=checksum for revision,checksum in actual.items()):
                raise RuntimeError('Schema migration checksum mismatch; an explicit reviewed migration is required.')
            return
        # Refuse to adopt tables that were created outside this migration.
        from sqlalchemy import inspect
        if any(inspect(conn).has_table(t) for t in metadata.tables):
            raise RuntimeError('Unversioned existing application tables; migration refused.')
        metadata.create_all(conn)
        conn.execute(text('INSERT INTO projectforge_migrations (revision,checksum) VALUES (:r,:c)'), {'r':'0001','c':digest})


def create_app(schema_path=None, database_url=None):
    selected = Path(schema_path or Path(__file__).with_name('schema.json'))
    schema = json.loads(selected.read_text())
    if schema_path is None:
        manifest = selected.parent.parent / 'migrations/0001.json'
        if json.loads(manifest.read_text()) != schema:
            raise RuntimeError('Migration manifest differs from runtime schema')
    url = database_url or os.environ.get('DATABASE_URL')
    if not url and schema['database'] == 'sqlite':
        url = 'sqlite:///development.db'
    if not url:
        raise RuntimeError('DATABASE_URL is required; use PostgreSQL or an explicit SQLite development database.')
    engine = create_engine(url, connect_args={'check_same_thread':False} if url.startswith('sqlite') else {}, pool_pre_ping=True)
    if engine.dialect.name not in ('sqlite','postgresql'):
        raise RuntimeError('Unsupported database')
    if engine.dialect.name != schema['database']:
        raise RuntimeError('Database provider differs from the approved schema')
    if engine.dialect.name == 'sqlite':
        @event.listens_for(engine, 'connect')
        def foreign_keys(dbapi, _):
            dbapi.execute('PRAGMA foreign_keys=ON')
    metadata = make_metadata(schema)
    @asynccontextmanager
    async def lifespan(app):
        migrate(engine, schema, metadata)
        yield
        engine.dispose()
    app = FastAPI(title=schema['title'], lifespan=lifespan)
    app.state.engine = engine
    for entity in schema['entities']:
        register_routes(app, engine, metadata.tables[entity['table_name']], entity)
    return app


def register_routes(app, engine, table, entity):
    fields = {}
    for field in entity['fields']:
        if field['is_primary_key']:
            continue
        datatype = StrictInt if field['data_type'] == 'integer' else StrictStr
        fields[field['name']] = ((datatype | None) if field['is_nullable'] else datatype, ...)
    def nonblank(value):
        if isinstance(value, str):
            value = value.strip()
            if not value or len(value) > 10000:
                raise ValueError('Text must contain 1–10000 non-whitespace characters')
        return value
    payload_model = create_model(entity['entity_name']+'Input', __config__=ConfigDict(extra='forbid'),
        __validators__={'nonblank':field_validator('*')(nonblank)}, **fields)
    primary = next(c for c in table.columns if c.primary_key)
    path = '/api/' + entity['table_name']

    def list_rows(limit: int = Query(100, ge=1, le=200), offset: int = Query(0, ge=0)):
        with engine.connect() as conn:
            return [dict(r) for r in conn.execute(select(table).order_by(primary).limit(limit).offset(offset)).mappings()]

    def create(payload):
        try:
            with engine.begin() as conn:
                key = conn.execute(table.insert().values(**payload.model_dump())).inserted_primary_key[0]
                return dict(conn.execute(select(table).where(primary == key)).mappings().one())
        except IntegrityError:
            raise HTTPException(409, 'Unique or relationship constraint violation')

    def update(record_id: int, payload):
        try:
            with engine.begin() as conn:
                result = conn.execute(table.update().where(primary == record_id).values(**payload.model_dump()))
                if not result.rowcount:
                    raise HTTPException(404, 'Record not found')
                return dict(conn.execute(select(table).where(primary == record_id)).mappings().one())
        except IntegrityError:
            raise HTTPException(409, 'Unique or relationship constraint violation')

    def delete(record_id: int):
        try:
            with engine.begin() as conn:
                result = conn.execute(table.delete().where(primary == record_id))
                if not result.rowcount:
                    raise HTTPException(404, 'Record not found')
            return Response(status_code=204)
        except IntegrityError:
            raise HTTPException(409, 'Referenced record cannot be deleted')

    create.__annotations__['payload'] = payload_model
    update.__annotations__['payload'] = payload_model
    for method, suffix, endpoint, status in [('GET','',list_rows,200),('POST','',create,201),
            ('PUT','/{record_id}',update,200),('DELETE','/{record_id}',delete,204)]:
        app.add_api_route(path+suffix, endpoint, methods=[method], status_code=status,
                         name=method+'_'+entity['table_name'])
