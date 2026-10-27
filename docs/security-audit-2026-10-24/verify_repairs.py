"""Reproducible post-repair checks; never use the user's demo database."""
import json, shutil, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'backend'))
from app.execution.sandbox.test_runner import TestRunner
from app.execution.sandbox.result_parser import ResultParser
HERE=Path(__file__).parent/'repairs'
HERE.mkdir(exist_ok=True)

def copy_sources(source,dest):
    allowed={'.py','.json','.ts','.tsx','.css','.html','.svg','.png','.webp','.jpg'}
    skip={'.venv','node_modules','__pycache__','.git','.projectforge','dist','.vite-cache'}
    for file in source.rglob('*'):
        relative=file.relative_to(source)
        if set(relative.parts)&skip or file.is_symlink():continue
        if file.is_file() and file.suffix in allowed and not file.name.startswith('.env'):
            target=dest/relative;target.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(file,target)

mode=sys.argv[1]
stage=HERE/mode
if mode=='platform':
    copy_sources(ROOT/'backend/app',stage/'backend/app')
    (stage/'backend/tests').mkdir(parents=True,exist_ok=True)
    for name in ('test_identity_runtime.py','conftest.py'):
        shutil.copyfile(ROOT/'backend/tests'/name,stage/'backend/tests'/name)
else:copy_sources(ROOT/'docs/ecommerce-evidence'/mode,stage)
runner=TestRunner(stage)
runner.executor.docker=r'C:\Users\HET\AppData\Local\Programs\DockerDesktop\resources\bin\docker.exe'
runner.executor.image='projectforge-relational-runtime:local'
if mode=='platform':
    raw=runner.executor.execute('python -m pytest backend/tests/test_identity_runtime.py -v --no-header -p no:cacheprovider',timeout_sec=120)
    results={'identity_regression':ResultParser.parse_pytest(raw.stdout,raw.stderr,raw.exit_code,raw.duration_ms).model_dump()}
else:
    if mode=='razorpay-app':
        from app.execution.sandbox.razorpay_gate import SOURCE as contract
        from app.execution.sandbox.razorpay_browser import SOURCE as browser
    else:
        from app.execution.sandbox.payment_gate import SOURCE as contract
        from app.execution.sandbox.payment_browser import SOURCE as browser
    if '--browser-only' in sys.argv:
        results=json.loads((HERE/(mode+'-results.json')).read_text(encoding='utf-8'))
    else:results={'payment_controls':runner._payment_gate('repair_controls',contract).model_dump()}
    results['browser_journey']=runner._payment_gate('repair_browser',browser).model_dump()
(HERE/(mode+'-results.json')).write_text(json.dumps(results,indent=2),encoding='utf-8')
print(json.dumps(results,indent=2))
sys.exit(0 if all(v['exit_code']==0 for v in results.values()) else 1)
