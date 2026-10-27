import json
import pytest
from fastapi.testclient import TestClient
from app.execution.spec.build_spec_models import (BuildSpec, DatabaseEntityDef, DatabaseFieldDef, APIEndpointDef, TechStackSelection)
from app.execution.spec.commerce_contract import RelationalContract, Relationship
from app.execution.agent.relational import sources, schema_for
from app.execution.agent.relational_runtime import create_app


def related_spec(database='SQLite'):
    return BuildSpec(project_id='RELATIONAL-CHECK', project_name='Related catalogue foundation', generation_mode='MODEL',
        source_generation_strategy='RELATIONAL_CRUD', tech_stack=TechStackSelection(primary_database=database, auth_provider='None',frontend_styling='CSS'),
        relational_contract=RelationalContract(relationships=[Relationship(source_table='products',source_column='category_id',target_table='categories',target_column='id')]),
        database_entities=[DatabaseEntityDef(entity_name='Category',table_name='categories',fields=[
            DatabaseFieldDef(name='id',data_type='integer',is_primary_key=True),DatabaseFieldDef(name='name',data_type='text',is_unique=True)]),
            DatabaseEntityDef(entity_name='Product',table_name='products',fields=[DatabaseFieldDef(name='id',data_type='integer',is_primary_key=True),
                DatabaseFieldDef(name='name',data_type='text'),DatabaseFieldDef(name='category_id',data_type='integer')])],
        api_endpoints=[APIEndpointDef(endpoint_id=method+table,method=method,path='/api/'+table+suffix,description=method,auth_required=False)
            for table in ('categories','products') for method,suffix in [('GET',''),('POST',''),('PUT','/{record_id}'),('DELETE','/{record_id}')]])


def test_related_crud_constraints_restart_and_migration_drift(tmp_path):
    spec = related_spec()
    schema = tmp_path/'schema.json'
    schema.write_text(json.dumps(schema_for(spec)))
    url = 'sqlite:///'+str(tmp_path/'data.db')
    with TestClient(create_app(schema,url)) as client:
        assert client.post('/api/categories',json={'name':'Books'}).status_code == 201
        assert client.post('/api/categories',json={'name':'Books'}).status_code == 409
        assert client.post('/api/categories',json={'name':'  '}).status_code == 422
        assert client.post('/api/products',json={'name':'Novel','category_id':999}).status_code == 409
        created = client.post('/api/products',json={'name':'Novel','category_id':1})
        assert created.status_code == 201
        product = created.json()['id']
        assert client.delete('/api/categories/1').status_code == 409
        assert client.put(f'/api/products/{product}',json={'name':'Edited','category_id':1}).status_code == 200
        assert client.post('/api/categories',json={'name':'Other','admin':True}).status_code == 422
    with TestClient(create_app(schema,url)) as restarted:
        assert restarted.get('/api/products').json()[0]['name'] == 'Edited'
        assert restarted.delete(f'/api/products/{product}').status_code == 204
        assert restarted.delete('/api/categories/1').status_code == 204
        assert restarted.get('/api/products').json() == []
    changed = json.loads(schema.read_text())
    changed['entities'][0]['fields'][1]['is_unique'] = False
    schema.write_text(json.dumps(changed))
    with pytest.raises(RuntimeError,match='checksum mismatch'):
        with TestClient(create_app(schema,url)):
            pass


def test_related_sources_and_contract_validation():
    spec = related_spec()
    generated = sources(spec)
    for path, source in generated.items():
        if path.endswith('.py'):
            compile(source,path,'exec')
    assert 'data-testid' in generated['frontend/src/Entity1.tsx']
    assert json.loads(generated['backend/app/schema.json']) == json.loads(generated['backend/migrations/0001.json'])
    spec.relational_contract.relationships[0].target_column = 'missing'
    with pytest.raises(ValueError,match='existing compatible'):
        sources(spec)


def test_related_compiler_rejects_auth_and_ambiguous_relationships():
    spec = related_spec()
    spec.api_endpoints[0].auth_required = True
    with pytest.raises(ValueError,match='unauthenticated'):
        sources(spec)
    spec = related_spec()
    spec.database_entities[0].relationships = ['has many products']
    with pytest.raises(ValueError,match='typed'):
        sources(spec)
