"""Structural and artifact checks; not a replacement for a PlantUML compiler."""
from pathlib import Path
import ast
import json
import re
import xml.etree.ElementTree as ET
from pypdf import PdfReader

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'docs/diagrams/corrected'
model=json.loads((OUT/'diagram-model.json').read_text(encoding='utf-8'))
checks=[]
def check(condition,text):
    checks.append({'check':text,'passed':bool(condition)})

definitions={}
for source in (ROOT/'backend/app').rglob('*.py'):
    for node in ast.walk(ast.parse(source.read_text(encoding='utf-8-sig'))):
        if isinstance(node,ast.ClassDef):definitions[node.name]=node

for pi,p in enumerate(model['class_views']):
    for key,n in p['nodes'].items():
        cls=n['name'].split('<')[0]
        check(cls in definitions or cls=='BaseModel',f'2.3{chr(97+pi)}: implemented class {cls}')
        check(n['x']>=0 and n['y']>=0 and n['x']+n['w']<=1123 and n['y']+n['h']<=794,f'{cls}: A4 class bounds')
        if cls in definitions:
            methods={m.name for m in definitions[cls].body if isinstance(m,(ast.FunctionDef,ast.AsyncFunctionDef))}
            for op in n['ops']:
                match=re.match(r'\+ (\w+)\(',op)
                if match:check(match[1] in methods,f'{cls}.{match[1]} exists')
    for e in p['edges']:
        check(e['a'] in p['nodes'] and e['b'] in p['nodes'],f'2.3{chr(97+pi)}: connector endpoints {e["a"]}->{e["b"]}')
        for key,point in [(e['a'],e['pts'][0]),(e['b'],e['pts'][-1])]:
            n=p['nodes'][key];x,y=point
            border=(x in (n['x'],n['x']+n['w']) and n['y']<=y<=n['y']+n['h']) or (y in (n['y'],n['y']+n['h']) and n['x']<=x<=n['x']+n['w'])
            check(border,f'{key}: connector anchored to class perimeter')
        for a,b in zip(e['pts'],e['pts'][1:]):
            for key,n in p['nodes'].items():
                if key in (e['a'],e['b']):continue
                # All class polylines are orthogonal; strict interior intersection is forbidden.
                cross=(a[0]==b[0] and n['x']<a[0]<n['x']+n['w'] and max(min(a[1],b[1]),n['y'])<min(max(a[1],b[1]),n['y']+n['h'])) or (a[1]==b[1] and n['y']<a[1]<n['y']+n['h'] and max(min(a[0],b[0]),n['x'])<min(max(a[0],b[0]),n['x']+n['w']))
                check(not cross,f'Connector {e["a"]}->{e["b"]} avoids unrelated {key}')

for p in model['sequence_views']:
    for m in p['messages']:
        check(0<=m['a']<len(p['parts']) and 0<=m['b']<len(p['parts']),f'{p["title"]}: message participant references')

sources=list(OUT.glob('*.puml'));check(len(sources)==6,'Exactly six PlantUML sources')
for f in sources:
    text=f.read_text(encoding='utf-8');check(text.count('@startuml')==1 and text.count('@enduml')==1,f'{f.name}: UML delimiters')
    if f.name.startswith('Figure_2_4'):
        blocks=[];active={}
        for line in text.splitlines():
            if line.startswith(('loop ','opt ','alt ')):blocks.append(line.split()[0])
            elif line=='end':
                check(bool(blocks),f'{f.name}: fragment end matches')
                if blocks:blocks.pop()
            elif line.startswith('else '):check(bool(blocks) and blocks[-1]=='alt',f'{f.name}: else belongs to alt')
            elif line.startswith('activate '):active[line.split()[1]]=active.get(line.split()[1],0)+1
            elif line.startswith('deactivate '):
                name=line.split()[1];active[name]=active.get(name,0)-1
                check(active[name]>=0,f'{f.name}: activation has a start')
        check(not blocks,f'{f.name}: balanced fragments')
        check(all(v==0 for v in active.values()),f'{f.name}: balanced activation totals')

pdfs=list(OUT.glob('*.pdf'));check(len(pdfs)==2,'Exactly two PDF deliverables')
for f in pdfs:
    doc=PdfReader(f);check(len(doc.pages)==3,f'{f.name}: exactly three pages')
    for i,p in enumerate(doc.pages):
        w,h=float(p.mediabox.width),float(p.mediabox.height)
        check(abs(w-841.89)<1 and abs(h-595.28)<1,f'{f.name} page {i+1}: A4 landscape')
        check(len(p.images)==0,f'{f.name} page {i+1}: native vector content, no rasterized diagram')
for f in OUT.glob('*.drawio'):
    root=ET.parse(f).getroot();check(len(root.findall('diagram'))==3,f'{f.name}: three editable pages')
    for d in root.findall('diagram'):
        cells=d.findall('mxGraphModel/root/mxCell');ids={c.get('id') for c in cells}
        check(all(c.get(k) is None or c.get(k) in ids for c in cells for k in ('parent','source','target')),f'{f.name}: resolved XML references')
(OUT/'validation-results.json').write_text(json.dumps(checks,indent=2),encoding='utf-8')
failed=[c for c in checks if not c['passed']]
print(f'{len(checks)-len(failed)}/{len(checks)} checks passed')
for c in failed:print('FAILED:',c['check'])
raise SystemExit(bool(failed))
