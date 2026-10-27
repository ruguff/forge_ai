import sys,json,shutil
from pathlib import Path
root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root/'backend'))
from app.execution.sandbox.test_runner import TestRunner
stage=root/'docs/shipment-evidence/platform'
for folder in ('app','tests'):
 for file in (root/'backend'/folder).rglob('*'):
  if '__pycache__' in file.parts or not file.is_file() or file.suffix not in {'.py','.json','.ts','.tsx','.css','.html','.svg'}:continue
  target=stage/'backend'/file.relative_to(root/'backend');target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(file,target)
runner=TestRunner(stage)
# The generated-app image does not include platform-only settings dependencies.
# Copy the already installed pure-Python packages into the disposable test tree.
for name in ('pydantic_settings','dotenv','typing_inspection'):
 package=root/'.venv/Lib/site-packages'/name
 if package.is_dir():shutil.copytree(package,stage/'backend'/name,dirs_exist_ok=True,ignore=shutil.ignore_patterns('__pycache__'))
runner.executor.docker=r'C:\Users\HET\AppData\Local\Programs\DockerDesktop\resources\bin\docker.exe'
runner.executor.image='projectforge-relational-runtime:local'
result=runner.executor.execute('python -m pytest backend/tests/test_orders_compiler.py backend/tests/test_payments_compiler.py backend/tests/test_razorpay_compiler.py -v --no-header -p no:cacheprovider',timeout_sec=120)
(stage.parent/'generator-results.json').write_text(result.model_dump_json(indent=2),encoding='utf-8')
print(result.stdout);print(result.stderr);sys.exit(result.exit_code)
