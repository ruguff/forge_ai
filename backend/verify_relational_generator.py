"""Independent acceptance gate for the related-data PostgreSQL foundation."""
import json
from pathlib import Path
from app.execution.agent.relational import prepare_spec
from app.execution.orchestrator.coding_orchestrator import CodingOrchestrator
from app.execution.sandbox.result_parser import ResultParser
from tests.test_relational import related_spec

RESTART_TEST = '''import subprocess
import time
import httpx
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from app.main import app

def start():
    process = subprocess.Popen(['python','-m','uvicorn','app.main:app','--host','127.0.0.1','--port','8001'])
    for _ in range(100):
        try:
            if httpx.get('http://127.0.0.1:8001/openapi.json').status_code == 200:
                return process
        except httpx.HTTPError:
            pass
        if process.poll() is not None:
            raise AssertionError('Backend exited before readiness')
        time.sleep(.1)
    process.terminate()
    process.wait(timeout=5)
    raise AssertionError('Backend readiness timeout')

def test_postgresql_constraints_and_process_restart():
    assert app.state.engine.dialect.name == 'postgresql'
    process = start()
    try:
        with httpx.Client(base_url='http://127.0.0.1:8001') as client:
            category = client.post('/api/categories',json={'name':'Books'})
            assert category.status_code == 201
            cid = category.json()['id']
            assert client.post('/api/categories',json={'name':'Books'}).status_code == 409
            assert client.post('/api/products',json={'name':'Invalid','category_id':99999}).status_code == 409
            product = client.post('/api/products',json={'name':'Novel','category_id':cid})
            assert product.status_code == 201
            pid = product.json()['id']
            assert client.delete('/api/categories/'+str(cid)).status_code == 409
            assert client.put('/api/products/'+str(pid),json={'name':'Edited','category_id':cid}).status_code == 200
            assert client.post('/api/products',json={'name':'  ','category_id':cid}).status_code == 422
            assert client.post('/api/products',json={'name':'Bad','category_id':cid,'id':9000}).status_code == 422
        import pytest
        with pytest.raises(IntegrityError), app.state.engine.begin() as conn:
            conn.execute(text("INSERT INTO products (name,category_id) VALUES ('Orphan',99999)"))
        with pytest.raises(IntegrityError), app.state.engine.begin() as conn:
            conn.execute(text("INSERT INTO categories (name) VALUES ('Books')"))
    finally:
        process.terminate()
        process.wait(timeout=5)
    process = start()
    try:
        with httpx.Client(base_url='http://127.0.0.1:8001') as client:
            assert client.get('/api/products').json() == [{'id':pid,'name':'Edited','category_id':cid}]
            assert client.delete('/api/products/'+str(pid)).status_code == 204
            assert client.delete('/api/categories/'+str(cid)).status_code == 204
            assert client.get('/api/products').json() == []
    finally:
        process.terminate()
        process.wait(timeout=5)
'''


def main():
    root = Path(__file__).resolve().parent.parent / 'docs/ecommerce-evidence/relational-app'
    spec = related_spec('PostgreSQL')
    spec.acceptance_checks = [
        {'method':'POST','path':'/api/categories','json':{'name':'Books'},'status':201,'body_contains':{'name':'Books'}},
        {'method':'POST','path':'/api/categories','json':{'name':'Books'},'status':409},
        {'method':'POST','path':'/api/products','json':{'name':'Novel','category_id':1},'status':201,'body_contains':{'name':'Novel','category_id':1}},
        {'method':'DELETE','path':'/api/categories/1','status':409}]
    spec.browser_checks = [{'name':'Related entity creation','steps':[
        {'action':'fill','selector':'[data-testid="categories-field-name"]','value':'Books'},
        {'action':'click','selector':'[data-testid="categories-create"]'},
        {'action':'text','selector':'[data-testid="categories-row"]','value':'Books'},
        {'action':'click','selector':'nav button:has-text("Product")'},
        {'action':'fill','selector':'[data-testid="products-field-name"]','value':'Novel'},
        {'action':'fill','selector':'[data-testid="products-field-category_id"]','value':'1'},
        {'action':'click','selector':'[data-testid="products-create"]'},
        {'action':'text','selector':'[data-testid="products-row"]','value':'Novel'}]}]
    spec = prepare_spec(spec)
    root.parent.mkdir(parents=True,exist_ok=True)
    (root.parent/'relational-build-spec.json').write_text(spec.model_dump_json(indent=2),encoding='utf-8')
    orchestrator = CodingOrchestrator(root)
    report = orchestrator.execute_build(spec)
    (root/'.projectforge/test_restart.py').write_text(RESTART_TEST,encoding='utf-8')
    execution = orchestrator.test_runner.executor.execute('python -m pytest /source/.projectforge/test_restart.py -v --no-header -p no:cacheprovider',timeout_sec=120)
    restart = ResultParser.parse_pytest(execution.stdout,execution.stderr,execution.exit_code,execution.duration_ms)
    evidence = {'build':report.model_dump(mode='json'),'postgresql_restart_constraints':restart.model_dump(mode='json'),
        'security':'UNVERIFIED','accessibility':'UNVERIFIED','performance':'UNVERIFIED','provider_integration':'NOT_IMPLEMENTED'}
    (root.parent/'relational-verification.json').write_text(json.dumps(evidence,indent=2),encoding='utf-8')
    assert report.status == 'VERIFIED', report
    assert restart.is_success, restart
    print('Related CRUD build, browser journey, PostgreSQL constraints and process restart passed.')


if __name__ == '__main__':
    main()
