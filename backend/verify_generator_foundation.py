"""Independent, offline UI-contract smoke test. Does not touch saved user projects."""
import json
from pathlib import Path
from app.execution.spec.build_spec_models import BuildSpec, UIContract, DatabaseEntityDef, DatabaseFieldDef, APIEndpointDef
from app.execution.agent.declarative import file_source
from app.execution.sandbox.test_runner import TestRunner


def main():
    root = Path(__file__).resolve().parent.parent / 'docs/ecommerce-evidence/foundation-app'
    contract = UIContract(namespace='tasks')
    spec = BuildSpec(project_id='FOUNDATION-CHECK', project_name='Foundation Task Manager', ui_contract=contract,
        database_entities=[DatabaseEntityDef(entity_name='Task', table_name='tasks', fields=[
            DatabaseFieldDef(name='id', data_type='integer', is_primary_key=True),
            DatabaseFieldDef(name='title', data_type='string'), DatabaseFieldDef(name='description', data_type='text')])],
        api_endpoints=[APIEndpointDef(endpoint_id=method, method=method, path=path, description=method, auth_required=False)
            for method,path in [('GET','/api/tasks'),('POST','/api/tasks'),('PUT','/api/tasks/{task_id}'),('DELETE','/api/tasks/{task_id}')]],
        acceptance_checks=[{'method':'POST','path':'/api/tasks','status':201}, {'method':'DELETE','path':'/api/tasks/1','status':204}])
    files = ['backend/app/__init__.py','backend/app/main.py','backend/requirements.txt','backend/tests/test_app.py',
        'frontend/package.json','frontend/tsconfig.json','frontend/vite.config.ts','frontend/src/App.tsx',
        'frontend/src/main.tsx','frontend/index.html','README.md']
    for name in files:
        target = root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(file_source(spec,name), encoding='utf-8')
    select = contract.selector
    steps = [
        {'action':'fill','selector':select('field-title'),'value':'Independent title'},
        {'action':'fill','selector':select('field-description'),'value':'Independent description'},
        {'action':'click','selector':select('create')},
        {'action':'text','selector':select('row',1),'value':'Independent title'},
        {'action':'goto','path':'/'},
        {'action':'text','selector':select('row',1),'value':'Independent description'},
        {'action':'click','selector':select('edit',1)},
        {'action':'fill','selector':select('field-title'),'value':'Edited title'},
        {'action':'click','selector':select('save')},
        {'action':'text','selector':select('row',1),'value':'Edited title'},
        {'action':'click','selector':select('delete',1)},
        {'action':'hidden','selector':select('row',1)}]
    runner = TestRunner(root)
    report = {'frontend_build':runner.run_frontend_build().model_dump(mode='json'),
              'browser_journeys':runner.run_browser_checks([{'name':'Independent CRUD journey','steps':steps}]).model_dump(mode='json')}
    (root.parent / 'foundation-verification.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    assert report['frontend_build']['exit_code'] == 0, report
    assert report['browser_journeys']['exit_code'] == 0, report
    print('Foundation frontend build and independent CRUD browser journey passed.')


if __name__ == '__main__':
    main()
