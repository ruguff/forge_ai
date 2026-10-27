"""Read demo distribution metadata; query public PyPI version advisory records only."""
import concurrent.futures, email, json, urllib.request
from pathlib import Path
HERE=Path(__file__).resolve().parent
site=HERE.parents[1]/'docs/ecommerce-evidence/payments-app/backend/.venv/Lib/site-packages'
packages=[]
for path in site.glob('*.dist-info/METADATA'):
    metadata=email.message_from_string(path.read_text(encoding='utf-8'))
    packages.append((metadata['Name'],metadata['Version']))
def check(item):
    name,version=item
    try:
        with urllib.request.urlopen('https://pypi.org/pypi/'+name+'/'+version+'/json',timeout=15) as response:
            data=json.load(response)
        return {'name':name,'version':version,'vulnerabilities':data.get('vulnerabilities',[]),'status':'checked'}
    except Exception as exc:return {'name':name,'version':version,'status':'unverified','error':type(exc).__name__}
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:results=list(pool.map(check,packages))
output={'method':'PyPI per-version advisory metadata, not a complete SCA scan','packages':results}
(HERE/'python-advisories.json').write_text(json.dumps(output,indent=2),encoding='utf-8')
print(json.dumps({'packages':len(results),'flagged':[(v['name'],v['version'],len(v['vulnerabilities'])) for v in results if v.get('vulnerabilities')],'unverified':[v['name'] for v in results if v['status']!='checked']}))
