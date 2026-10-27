"""Explicit recovery of the diagnosed Task Manager browser-contract failure.

Build a new version without changing the live API's cached project state.
The original v2 workspace and saved snapshot remain untouched.
"""
import copy
import json
import sqlite3
import socket
import sys
from pathlib import Path

from app.agents.model_client import LocalModelClient
from app.execution.orchestrator.coding_orchestrator import CodingOrchestrator
from app.execution.spec.build_spec_models import BuildSpec
from app.execution.spec.model_compiler import validate_spec
from app.models.schemas import ProjectContext


def main():
    project_id = 'PROJ-7F5BD586F492'
    with sqlite3.connect('file:data/projects.sqlite3?mode=ro', uri=True) as db:
        row = db.execute('SELECT payload FROM snapshots WHERE project_id=?', (project_id,)).fetchone()
    if not row:
        raise RuntimeError('Saved Task Manager project not found')
    snapshot = json.loads(row[0])
    context = ProjectContext.model_validate(snapshot['context'])
    spec = BuildSpec.model_validate(snapshot['spec'])
    if spec.version != 2 or len(spec.browser_checks) != 3:
        raise RuntimeError('Recovery requires the inspected v2 contract; inspect changed input first')
    original = copy.deepcopy(spec.browser_checks)
    delete = spec.browser_checks[2]
    if delete['name'] != 'Delete Task Flow' or delete['steps'][-1]['action'] != 'visible':
        raise RuntimeError('Unexpected deletion contract; no automatic correction applied')
    # The preceding edit journey changes record 1's title. Deletion must prove
    # that this existing record disappears, not expect old/unrelated data.
    target = ".task-list .task-item[title='Edited Title']"
    delete['steps'].insert(1, {'action': 'visible', 'selector': target})
    delete['steps'][-1] = {'action': 'hidden', 'selector': target}
    # Check actual field values, in addition to locating the record by title.
    spec.browser_checks[0]['steps'].append({
        'action': 'text', 'selector': ".task-item[title='Task Title'] .record-description",
        'value': 'Task Description'})
    spec.browser_checks[1]['steps'].append({
        'action': 'text', 'selector': ".task-item[title='Edited Title'] .record-description",
        'value': 'Edited Description'})
    spec.version = context.version + 1
    errors = validate_spec(spec, context)
    if errors:
        raise RuntimeError(errors)
    workspace = Path('generated_projects') / project_id / f'v{spec.version}'
    if workspace.exists():
        raise RuntimeError('Recovery workspace already exists; inspect its report rather than overwrite it')
    notes = Path('../docs/task-manager-recovery')
    notes.mkdir(parents=True, exist_ok=True)
    (notes / 'browser-contract-correction.json').write_text(json.dumps({
        'project_id': project_id, 'original_version': 2, 'recovery_version': spec.version,
        'reason': 'Correct the deletion postcondition; preserve all three CRUD journeys and add description assertions.',
        'before': original, 'after': spec.browser_checks,
        'live_snapshot_modified': False,
    }, indent=2), encoding='utf-8')
    report = CodingOrchestrator(workspace, model_client=LocalModelClient(),
        on_event_callback=lambda kind, data: print(kind, flush=True)).execute_build(spec)
    (notes / 'build-report.json').write_text(report.model_dump_json(indent=2), encoding='utf-8')
    print(report.model_dump_json(indent=2), flush=True)


def adopt_verified_recovery():
    from app.api.persistence import ProjectPersistence
    from app.execution.verification import source_digest
    from app.models.schemas import ProjectState
    with socket.socket() as client:
        if client.connect_ex(('127.0.0.1', 8000)) == 0:
            raise RuntimeError('Stop the backend before updating its cached project snapshot')
    project_id = 'PROJ-7F5BD586F492'
    with sqlite3.connect('file:data/projects.sqlite3?mode=ro', uri=True) as db:
        snapshot = json.loads(db.execute('SELECT payload FROM snapshots WHERE project_id=?',
                                       (project_id,)).fetchone()[0])
    context = ProjectContext.model_validate(snapshot['context'])
    state = ProjectState.model_validate(snapshot['state'])
    if context.version != 2 or context.execution_state not in ('REQUIRES_HUMAN', 'FAILED'):
        raise RuntimeError('Project has changed since diagnosis; inspect before adopting')
    workspace = Path('generated_projects') / project_id / 'v3'
    report = json.loads((workspace / '.projectforge/verification.json').read_text(encoding='utf-8'))
    spec = BuildSpec.model_validate_json((workspace / '.projectforge/build_spec.json').read_text(encoding='utf-8'))
    if (report['status'] != 'VERIFIED' or report['source_digest'] != source_digest(workspace)
            or not all(value == 'PASSED' for value in report['verification_checks'].values())):
        raise RuntimeError('Recovery does not have current passing verification evidence')
    if spec.project_id != project_id or spec.version != 3 or validate_spec(spec, context):
        raise RuntimeError('Recovery contract does not match this project')
    backup = Path('../docs/task-manager-recovery/snapshot-before-adoption.json')
    with backup.open('x', encoding='utf-8') as output:
        json.dump(snapshot, output, indent=2)
    context.version = 3
    context.execution_state = 'VERIFIED'
    context.build_spec = spec.model_dump(mode='json')
    context.agent_outputs['build_report'] = report
    context.agent_outputs['browser_contract_recovery'] = {
        'original_version': 2, 'verified_version': 3,
        'reason': 'Reviewed deletion postcondition and corrected live DOM selector mapping.'}
    state.revision += 1
    persistence = ProjectPersistence()
    persistence.save(project_id, state, context, spec)
    persistence.append_event(project_id, {'type': 'VERIFICATION_SUCCESS', 'agent_id': 'coding_agent',
        'message': 'Reviewed browser-contract recovery v3 passed all declared checks.',
        'data': {'version': 3, 'checks': report['verification_checks']}})
    print('Saved verified v3 recovery. Restart the backend to reload it.')


if __name__ == '__main__':
    adopt_verified_recovery() if '--adopt' in sys.argv else main()
