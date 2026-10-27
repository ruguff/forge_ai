"""Run the fixed local demonstration brief through the public planning API."""
import json
import time
from pathlib import Path
import httpx

BRIEF = ('Build a small single-user notes website. Use React 18, TypeScript 5, Vite 5, '
         'FastAPI and local SQLite. Users can create a note with a required title and body, '
         'list notes, edit notes and delete notes. Persist notes across server restarts. '
         'Use a simple responsive interface. No login, collaboration, AI features, cloud '
         'services or external integrations. This is a local student demo for one user; '
         'no public deployment or high-scale availability is required.')
report = Path('../docs/offline-baseline.json')
with httpx.Client(base_url='http://127.0.0.1:8000', timeout=900, trust_env=False) as client:
    response = client.post('/api/projects', json={'idea': BRIEF, 'mode': 'AUTONOMOUS'})
    response.raise_for_status()
    project = response.json()
    project_id = project['project_id']
    print(project_id, flush=True)
    report.write_text(json.dumps({'project_id': project_id, 'brief': BRIEF}, indent=2), encoding='utf-8')
    start = time.monotonic()
    response = client.post(f'/api/projects/{project_id}/understand')
    response.raise_for_status()
    understanding = response.json()
    report.write_text(json.dumps({'project_id': project_id, 'brief': BRIEF,
        'understanding_seconds': round(time.monotonic()-start, 1), 'understanding': understanding}, indent=2), encoding='utf-8')
    print(json.dumps({'understanding_state': understanding['execution_state'], 'clarification': understanding.get('clarification')}), flush=True)
    if understanding['execution_state'] == 'REQUIREMENTS_VALIDATED':
        response = client.post(f'/api/projects/{project_id}/analyze')
        response.raise_for_status()
        print(json.dumps(response.json()), flush=True)
