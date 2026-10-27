"""Recheck an existing specification without rerunning model planning.

Diagnostic results do not overwrite the live project's recorded state.
"""
import argparse
import json
from pathlib import Path
from app.agents.model_client import LocalModelClient
from app.execution.orchestrator.coding_orchestrator import CodingOrchestrator
from app.execution.spec.build_spec_models import BuildSpec

parser = argparse.ArgumentParser()
parser.add_argument('workspace', type=Path)
args = parser.parse_args()
workspace = args.workspace.resolve()
if not workspace.is_relative_to(Path('generated_projects').resolve()):
    raise ValueError('Workspace must be inside generated_projects')
spec = BuildSpec.model_validate_json((workspace / '.projectforge/build_spec.json').read_text(encoding='utf-8'))
report = CodingOrchestrator(workspace, model_client=LocalModelClient()).execute_build(spec)
(workspace / '.projectforge/recheck_report.json').write_text(
    json.dumps(report.model_dump(mode='json'), indent=2), encoding='utf-8')
print('Diagnostic verification status:', report.status, flush=True)
print(json.dumps(report.verification_checks), flush=True)
