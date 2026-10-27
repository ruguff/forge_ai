"""Generate and verify a reviewed read-only catalogue from a typed specification."""
import argparse
import json
from pathlib import Path
from app.execution.agent.catalogue import prepare_spec
from app.execution.spec.build_spec_models import BuildSpec
from app.execution.orchestrator.coding_orchestrator import CodingOrchestrator


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--spec',required=True,type=Path)
    parser.add_argument('--output',required=True,type=Path)
    parser.add_argument('--resume',action='store_true')
    args=parser.parse_args()
    spec=prepare_spec(BuildSpec.model_validate_json(args.spec.read_text(encoding='utf-8')))
    report=CodingOrchestrator(args.output).execute_build(spec,resume=args.resume)
    print(json.dumps(report.model_dump(mode='json'),indent=2))
    if report.status!='VERIFIED':raise SystemExit(1)


if __name__=='__main__':main()
