"""Generate the validated diagnostic specification; verification stays sandboxed."""
import json
import sqlite3
from pathlib import Path
from app.agents.model_client import LocalModelClient
from app.execution.spec.build_spec_models import BuildSpec
from app.execution.orchestrator.coding_orchestrator import CodingOrchestrator

saved = json.loads(Path('../docs/offline-continuation.json').read_text(encoding='utf-8'))
spec = BuildSpec.model_validate(saved['build_spec'])
from app.config import get_settings
if get_settings().LOCAL_CODE_GENERATION_STRATEGY == 'declarative_crud':
    spec.source_generation_strategy = 'DECLARATIVE_CRUD'
from app.execution.spec.local_compiler import runtime_manifest
from app.execution.spec.model_compiler import validate_spec
from app.models.schemas import ProjectContext
spec.files_to_create = runtime_manifest(spec.files_to_create, spec.project_type.value, [r.id for r in spec.requirements])
with sqlite3.connect('data/projects.sqlite3') as db:
    snapshot = json.loads(db.execute('SELECT payload FROM snapshots WHERE project_id=?', (spec.project_id,)).fetchone()[0])
context = ProjectContext.model_validate(snapshot['context'])
if context.version != spec.version:
    raise RuntimeError('Diagnostic specification is stale; recompile current requirements.')
errors = validate_spec(spec, context)
if errors:
    raise RuntimeError('Diagnostic spec must pass current validation before generation: ' + '; '.join(errors))
workspace = Path('generated_projects') / spec.project_id / 'offline-reliability-v2'
def event(kind, data):
    if kind in ('TASK_STARTED', 'TASK_COMPLETED', 'TASK_FAILED', 'BUILD_BLOCKED'):
        print(json.dumps({'type': kind, 'data': data}), flush=True)
model = LocalModelClient()
report = CodingOrchestrator(workspace, on_event_callback=event, model_client=model).execute_build(spec)
Path('../docs/offline-build-report.json').write_text(json.dumps({
    'report': report.model_dump(mode='json'), 'model_usage': model.usage()}, indent=2), encoding='utf-8')
print('Final source-generation status: ' + report.status, flush=True)
