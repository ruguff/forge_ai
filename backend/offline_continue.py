"""Diagnostic continuation from saved artifacts; does not overwrite the live project."""
import asyncio
import json
import sqlite3
import time
from pathlib import Path
from app.agents.model_client import LocalModelClient
from app.agents.security_agent import SecurityAgent
from app.agents.qa_agent import QAAgent
from app.models.schemas import ProjectState, ProjectContext
from app.execution.spec.model_compiler import compile_model

async def main():
    with sqlite3.connect('data/projects.sqlite3') as db:
        saved = json.loads(db.execute('select payload from snapshots where project_id=?', ('PROJ-FCC520C200D2',)).fetchone()[0])
    state, context = ProjectState.model_validate(saved['state']), ProjectContext.model_validate(saved['context'])
    report = {}
    previous_path = Path('../docs/offline-continuation.json')
    previous = json.loads(previous_path.read_text(encoding='utf-8')) if previous_path.exists() else {}
    for name, agent in [('security_report', SecurityAgent), ('qa_spec', QAAgent)]:
        # Diagnostic-only reuse of successful output from this fixed snapshot.
        if previous.get(name, {}).get('success'):
            value = ProjectState.model_fields[name].annotation
            from pydantic import TypeAdapter
            setattr(state, name, TypeAdapter(value).validate_python(previous[name]['output']))
            report[name] = previous[name]
            continue
        inputs = state.model_dump(mode='json')
        inputs['project_context'] = {key: context.model_dump(mode='json')[key] for key in
            ('raw_request', 'version', 'requirements', 'constraints', 'decisions', 'mode')}
        model = LocalModelClient()
        start = time.monotonic()
        try:
            result = await agent(model.generate).analyze(inputs)
            report[name] = {'success': result.success, 'attempts': result.attempts,
                'seconds': round(time.monotonic()-start, 1), 'usage': model.usage(),
                'errors': result.validation_errors + result.lint_violations,
                'output': result.output.model_dump(mode='json') if result.success else None}
            if result.success:
                setattr(state, name, result.output)
        except Exception as exc:
            report[name] = {'success': False, 'error': str(exc)}
        Path('../docs/offline-continuation.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
        print(json.dumps({name: {k:v for k,v in report[name].items() if k != 'output'}}), flush=True)
        if not report[name]['success']:
            return
    try:
        spec = await compile_model(context, state, LocalModelClient().generate)
        report['build_spec'] = spec.model_dump(mode='json')
    except Exception as exc:
        report['compiler_error'] = str(exc)
    Path('../docs/offline-continuation.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print('Compilation: ' + report.get('compiler_error', 'passed'), flush=True)

if __name__ == '__main__':
    asyncio.run(main())
