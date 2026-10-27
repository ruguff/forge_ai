"""Explicit live diagnostic; reads a saved project without changing its state."""
import asyncio
import json
import sqlite3
import time
from pathlib import Path

from app.agents.model_client import LocalModelClient
from app.agents.engineering_agent import EngineeringAgent
from app.agents.project_understanding_agent import ProjectUnderstandingAgent


async def main():
    with sqlite3.connect('data/projects.sqlite3') as db:
        row = db.execute('SELECT payload FROM snapshots WHERE project_id=?',
                         ('PROJ-A75D33D78D43',)).fetchone()
    if not row:
        raise RuntimeError('Saved failed project not found')
    snapshot = json.loads(row[0])
    context = snapshot['context']
    inputs = snapshot['state']
    inputs['project_context'] = {key: context[key] for key in (
        'raw_request', 'version', 'requirements', 'constraints', 'decisions', 'mode')}
    inputs['project_context']['execution_capabilities'] = {
        'supported_stack': 'React 18 + TypeScript 5 + Vite 5 + FastAPI + local SQLite',
        'external_services': 'Unavailable in the offline verification container',
        'instruction': 'Respect user choices. Report incompatible explicit choices as limitations; do not silently substitute technologies.',
    }
    results = {}
    for name in ('engineering', 'understanding'):
        model = LocalModelClient()
        start = time.monotonic()
        if name == 'engineering':
            result = await EngineeringAgent(model.generate).analyze(inputs)
        else:
            result = await ProjectUnderstandingAgent(model.generate).analyze_project_idea(context['raw_request'])
        summary = {'success': result.success, 'attempts': result.attempts,
                   'elapsed_seconds': round(time.monotonic() - start, 1),
                   'validation_errors': result.validation_errors, 'lint_violations': result.lint_violations,
                   'usage': model.usage()}
        results[name] = {**summary, 'output': result.output.model_dump(mode='json') if result.success else None}
        print(json.dumps({name: summary}), flush=True)
        Path('../docs/local-stage-retest.json').write_text(json.dumps(results, indent=2), encoding='utf-8')


if __name__ == '__main__':
    asyncio.run(main())
