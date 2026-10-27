import ast
import json
import pytest
from types import SimpleNamespace
from app.execution.spec.build_spec_models import BuildSpec, DatabaseEntityDef, DatabaseFieldDef, APIEndpointDef
from app.execution.agent.local_backend import build_module


def specification():
    return BuildSpec(project_id='PROJ-BODY-TEST', project_name='Notes',
        database_entities=[DatabaseEntityDef(entity_name='Note',table_name='notes',fields=[
            DatabaseFieldDef(name='id',data_type='integer',is_primary_key=True),
            DatabaseFieldDef(name='title',data_type='string')])],
        api_endpoints=[APIEndpointDef(endpoint_id='CREATE',method='POST',path='/api/notes',description='Create',auth_required=False),
            APIEndpointDef(endpoint_id='DELETE',method='DELETE',path='/api/notes/{note_id}',description='Delete',auth_required=False)],
        acceptance_checks=[{'method':'POST','path':'/api/notes','status':201},
            {'method':'DELETE','path':'/api/notes/1','status':204}])


def test_scaffold_owns_injection_and_statuses_but_model_supplies_bodies():
    responses = {'handlers': {'CREATE':'row = Model(**payload)\ndb.add(row)\ndb.commit()\ndb.refresh(row)\nreturn row',
        'DELETE':'row = db.get(Model, item_id)\nif row is None:\n    raise HTTPException(404, "Not found")\ndb.delete(row)\ndb.commit()\nreturn None'}}
    calls = []
    def generate(prompt, **kwargs):
        calls.append(prompt)
        body = responses['handlers']['CREATE' if '"method": "POST"' in prompt else 'DELETE']
        return json.dumps({'lines': body.splitlines()})
    source = build_module(specification(), SimpleNamespace(generate_sync=generate))
    ast.parse(source)  # No import/exec of generated source.
    assert 'status_code=201' in source and 'status_code=204' in source
    assert 'db: Session = Depends(_get_db)' in source
    assert 'db.add(row)' in source
    assert len(calls) == 2


def test_unknown_bindings_do_not_fall_back_to_template_handlers():
    model = SimpleNamespace(generate_sync=lambda *a, **k: json.dumps({'lines':[
        'row = Model(**payload)', 'db.add(row)', 'db.commit()', 'return unknown_magic()']}))
    with pytest.raises(ValueError, match='Unknown handler bindings'):
        build_module(specification(), model)
