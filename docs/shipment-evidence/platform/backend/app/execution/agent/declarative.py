"""Explicit local CRUD compiler; never an automatic fallback for arbitrary requests."""
import json
import re
from app.execution.agent.local_backend import build_module


def validate_scope(spec):
    if spec.order_contract is not None or spec.identity_contract is not None or spec.catalogue_contract is not None or spec.relational_contract is not None:
        raise ValueError('Typed catalogue/relational contracts require their reviewed strategy, not single-entity CRUD.')
    if spec.commerce_contract is not None:
        raise ValueError('Commerce execution is not implemented by DECLARATIVE_CRUD; commerce rules cannot be silently omitted.')
    if len(spec.database_entities) != 1:
        raise ValueError('DECLARATIVE_CRUD currently supports one entity; other projects require a different generation strategy.')
    entity = spec.database_entities[0]
    if entity.relationships or len([f for f in entity.fields if f.is_primary_key]) != 1:
        raise ValueError('DECLARATIVE_CRUD requires one primary key and no relationships.')
    primary = next(f for f in entity.fields if f.is_primary_key)
    if primary.data_type.lower() not in ('int','integer') or any(f.data_type.lower() not in ('int','integer','str','string','text','float','number') for f in entity.fields):
        raise ValueError('DECLARATIVE_CRUD currently supports an integer primary key and text/number fields; other types require an extended runtime.')
    if any(e.auth_required for e in spec.api_endpoints):
        raise ValueError('DECLARATIVE_CRUD does not implement authentication; no auth bypass is generated.')
    collections = [e for e in spec.api_endpoints if e.method=='GET' and '{' not in e.path]
    creates = [e for e in spec.api_endpoints if e.method=='POST' and '{' not in e.path]
    updates = [e for e in spec.api_endpoints if e.method in ('PUT','PATCH') and e.path.count('{')==1]
    deletes = [e for e in spec.api_endpoints if e.method=='DELETE' and e.path.count('{')==1]
    if not all(len(group)==1 for group in (collections, creates, updates, deletes)):
        raise ValueError('DECLARATIVE_CRUD requires explicit list/create/update/delete endpoint contracts.')
    if len(spec.api_endpoints) not in (4,5) or any(e.method not in ('GET','POST','PUT','PATCH','DELETE') for e in spec.api_endpoints):
        raise ValueError('Additional custom business endpoints are outside DECLARATIVE_CRUD; they are not silently omitted.')
    if collections[0].path != creates[0].path:
        raise ValueError('Local CRUD collection and create paths must match.')
    for requirement in spec.requirements:
        if requirement.source.value != 'USER' or requirement.dimension not in ('functional','functional_requirements'):
            continue
        text = requirement.description.lower()
        if any(word in text for word in ('payment','upload','classification','prediction','search','filter','export','import','collaborat','notification','authentication','login')):
            raise ValueError(f'{requirement.id} needs functionality beyond DECLARATIVE_CRUD; choose another strategy.')
    return collections[0], creates[0], updates[0], deletes[0]


def file_source(spec, path):
    get, post, put, delete = validate_scope(spec)
    if path == 'backend/app/main.py':
        return build_module(spec, None, declarative=True)
    if path == 'backend/app/__init__.py':
        return '"""Generated application package."""\n'
    if path == 'backend/requirements.txt':
        return 'fastapi>=0.115,<1\nuvicorn>=0.30,<1\nsqlalchemy>=2,<3\npydantic>=2,<3\npytest>=8,<9\nhttpx>=0.27,<1\n'
    if path == 'frontend/package.json':
        return json.dumps({'name':'generated-local-crud','version':'1.0.0','private':True,'type':'module',
            'scripts':{'dev':'vite','build':'tsc --noEmit && vite build','preview':'vite preview'},
            'dependencies':{'react':'^18.3.1','react-dom':'^18.3.1'},
            'devDependencies':{'typescript':'^5.4.5','vite':'6.4.5','@vitejs/plugin-react':'4.7.0','@types/react':'^18','@types/react-dom':'^18'}},indent=2)
    if path == 'frontend/tsconfig.json':
        return json.dumps({'compilerOptions':{'target':'ES2022','module':'ESNext','moduleResolution':'Bundler',
            'lib':['DOM','DOM.Iterable','ES2022'],'jsx':'react-jsx','strict':True,'noEmit':True,
            'esModuleInterop':True,'skipLibCheck':True},'include':['src','vite.config.ts']},indent=2)
    if path == 'frontend/vite.config.ts':
        return "import { defineConfig } from 'vite';\nimport react from '@vitejs/plugin-react';\nexport default defineConfig({cacheDir:'.vite-cache',plugins:[react()],server:{host:'127.0.0.1',port:3001,proxy:{'/api':'http://127.0.0.1:8001'}}});\n"
    if path == 'frontend/src/main.tsx':
        return "import React from 'react';\nimport {createRoot} from 'react-dom/client';\nimport App from './App';\ncreateRoot(document.getElementById('root')!).render(<React.StrictMode><App/></React.StrictMode>);\n"
    if path == 'frontend/index.html':
        return '<!doctype html><html><head><meta charset="UTF-8"/><meta name="viewport" content="width=device-width,initial-scale=1.0"/><title>Local application</title></head><body style="margin:0"><div id="root"></div><script type="module" src="/src/main.tsx"></script></body></html>\n'
    if path == 'frontend/src/App.tsx':
        return frontend_source(spec, (get,post,put,delete))
    if path == 'backend/tests/test_app.py':
        return ('from fastapi.testclient import TestClient\nfrom app.main import app\n'
                'def test_invalid_create_has_no_side_effect():\n    with TestClient(app) as client:\n'
                f'        response = client.post({post.path!r}, json={{}})\n'
                '        assert response.status_code == 422\n'
                f'        assert client.get({get.path!r}).status_code == 200\n')
    if path == 'README.md':
        return f'''# {spec.project_name}

Source compiled from the validated AI-designed specification using DECLARATIVE_CRUD.
This mode supports an unauthenticated single-entity CRUD application. It does not claim arbitrary code synthesis.
Verification results are stored separately; source generation alone does not establish working behavior.

Backend: `cd backend`, install requirements in a virtual environment, then `python -m uvicorn app.main:app --host 127.0.0.1 --port 8001`.
Frontend: `cd frontend`, `npm install --ignore-scripts`, then `npm run dev` (http://127.0.0.1:3001).
Tests: run `python -m pytest tests` from backend after installing requirements.
Data persists in backend/notes.db; PROJECTFORGE_DATABASE_PATH can select a separate database for testing.
'''
    raise ValueError(f'File {path} is outside the supported declarative runtime; no placeholder is generated.')


def frontend_source(spec, endpoints):
    entity = spec.database_entities[0]
    fields = [f for f in entity.fields if not f.is_primary_key]
    pk = next(f.name for f in entity.fields if f.is_primary_key)
    ids = {f.name: f'{f.name}-input' for f in fields}
    buttons = {'create':'create-record-btn','edit':'edit-record-btn','delete':'delete-record-btn'}
    classes = {'list':'record-list','item':'record-item','edit':'edit-record','delete':'delete-record',
               'create':'create-record','save':'save-record'}
    field_classes = {f.name:f'record-{f.name}' for f in fields}
    row_attributes = set()
    action_labels = {}
    for journey in ([] if spec.ui_contract else spec.browser_checks):
        name = journey['name'].lower()
        kind = 'delete' if 'delete' in name else 'edit' if any(x in name for x in ('edit','update')) else 'create'
        for step in journey['steps']:
            selector = step.get('selector','')
            simple = re.fullmatch(r'#([A-Za-z][\w-]*)', selector)
            if step['action']=='fill' and simple:
                field = next((f for f in fields if f.name.lower() in simple[1].lower()), None)
                if not field:
                    raise ValueError(f'Cannot bind input selector {selector} to a declared field.')
                ids[field.name] = simple[1]
            if step['action']=='click' and simple:
                buttons[kind] = simple[1]
            matches = re.findall(r'\.([A-Za-z][\w-]*)', selector)
            for attribute, _, value in re.findall(r'\[([\w-]+)=([\'\"])(.*?)\2\]', selector):
                if step['action'] in ('visible', 'hidden', 'text') and attribute in {f.name for f in fields}:
                    # Bind to live record values, never hard-code expected test data.
                    row_attributes.add(attribute)
                if step['action'] == 'click' and attribute == 'aria-label' and kind in ('edit', 'delete'):
                    label = re.fullmatch(r'(.*?)(\d+)([^\d]*)', value)
                    if not label:
                        raise ValueError(f'Row action label must include the record ID: {value}')
                    action_labels[kind] = [label[1], label[3]]
            if step['action'] == 'click' and matches:
                control = 'save' if kind == 'edit' and 'save' in matches[-1].lower() else kind
                classes[control] = matches[-1]
            if len(matches)>=2:
                classes['list'] = matches[0]
                if step['action'] in ('visible', 'hidden', 'text') and any(
                        word in matches[-1].lower() for word in ('item', 'card', 'row')):
                    classes['item'] = matches[-1]
                for field in fields:
                    if field.name.lower() in matches[-1].lower():
                        field_classes[field.name] = matches[-1]
    config = {'title':spec.project_name,'fields':[{'name':f.name,'label':f.name.replace('_',' ').title(),
              'id':ids[f.name],'className':field_classes[f.name],'multiline':f.data_type.lower()=='text' or f.name.lower() in ('body','description'),
              'numeric':f.data_type.lower() in ('int','integer','float','number')} for f in fields],
              'pk':pk,'buttons':buttons,'classes':classes,
              'rowAttributes':sorted(row_attributes),'actionLabels':action_labels,
              'api':{name: endpoint.path for name,endpoint in zip(('list','create','edit','delete'),endpoints)},
              'updateMethod':endpoints[2].method}
    config['uiNamespace'] = spec.ui_contract.namespace if spec.ui_contract else 'records'
    return FRONTEND.replace('__CONFIG__',json.dumps(config))


FRONTEND = '''import {useEffect,useState} from 'react';
const config = __CONFIG__;
type Row = Record<string,string|number|boolean|null>;
type Values = Record<string,string>;
export default function App(){
 const [rows,setRows]=useState<Row[]>([]),[values,setValues]=useState<Values>({}),[editing,setEditing]=useState<string|number|null>(null),[busy,setBusy]=useState(false),[error,setError]=useState('');
 const [loading,setLoading]=useState(true);
 const actionLabel=(action:'edit'|'delete',row:Row)=>{const labels:Record<string,string[]>=config.actionLabels;const label=labels[action];return label?label[0]+String(row[config.pk])+label[1]:undefined;};
 const url=(pattern:string,id:string|number)=>pattern.replace(/\\{[^}]+\\}/,encodeURIComponent(String(id)));
 const load=async()=>{try{const r=await fetch(config.api.list);if(!r.ok)throw new Error('Unable to load records');setRows(await r.json());}catch(e){setError(String(e));}finally{setLoading(false);}};
 useEffect(()=>{void load();},[]);
 const run=async(action:'create'|'edit'|'delete',row?:Row)=>{
  setBusy(true);setError('');
  try{
   const id=row?.[config.pk]??editing??rows[0]?.[config.pk];
   if(action!=='create'&&(id===undefined||id===null||typeof id==='boolean'))throw new Error('Choose a record first');
   const payload:Record<string,string|number>={};
   for(const field of config.fields){const value=values[field.name]??'';if(action==='create'||value.trim())payload[field.name]=field.numeric?Number(value):value;}
   const r=await fetch(action==='create'?config.api.create:url(config.api[action],id as string|number),{method:action==='create'?'POST':action==='edit'?config.updateMethod:'DELETE',headers:{'Content-Type':'application/json'},...(action==='delete'?{}:{body:JSON.stringify(payload)})});
   if(!r.ok){const data=await r.json().catch(()=>({detail:'Request failed'}));throw new Error(typeof data.detail==='string'?data.detail:JSON.stringify(data.detail));}
   setValues({});setEditing(null);await load();
  }catch(e){setError(String(e));}finally{setBusy(false);}
 };
 return <main style={{fontFamily:'system-ui,sans-serif',maxWidth:960,margin:'0 auto',padding:28,color:'#182536'}}>
 <h1>{config.title}</h1><p>Local data, saved on this device.</p>
 <section style={{display:'grid',gap:14,padding:22,background:'#f1f5f9',borderRadius:16}}>
 {config.fields.map(field=><label key={field.name} style={{display:'grid',gap:6}}>{field.label}{field.multiline?<textarea data-testid={config.uiNamespace+"-field-"+field.name} id={field.id} value={values[field.name]??''} onChange={e=>setValues({...values,[field.name]:e.target.value})} rows={4}/>:<input data-testid={config.uiNamespace+"-field-"+field.name} id={field.id} type={field.numeric?'number':'text'} value={values[field.name]??''} onChange={e=>setValues({...values,[field.name]:e.target.value})}/>}</label>)}
 <div style={{display:'flex',flexWrap:'wrap',gap:10}}><button data-testid={config.uiNamespace+"-create"} id={config.buttons.create} className={config.classes.create} disabled={busy} onClick={()=>void run('create')}>Create</button><button data-testid={config.uiNamespace+"-save"} id={config.buttons.edit} className={config.classes.save} disabled={busy||!rows.length} onClick={()=>void run('edit')}>Save changes</button><button id={config.buttons.delete} disabled={busy||!rows.length} onClick={()=>void run('delete')}>Delete selected</button></div>
 </section>{error&&<p data-testid={config.uiNamespace+"-error"} role="alert" style={{color:'#b42318'}}>{error}</p>}{loading&&<p data-testid={config.uiNamespace+"-loading"} role="status">Loading…</p>}
 <section data-testid={config.uiNamespace+"-list"} className={config.classes.list} style={{display:'grid',gap:12,marginTop:24}}>{!loading&&!rows.length&&<p>No records yet. Create your first record above.</p>}{rows.map(row=><article data-testid={config.uiNamespace+"-row"} data-record-id={String(row[config.pk])} className={config.classes.item} key={String(row[config.pk])} {...Object.fromEntries(config.rowAttributes.map(name=>[name,String(row[name]??'')]))} style={{padding:20,border:'1px solid #d4dce5',borderRadius:12}}>
 {config.fields.map(field=><p key={field.name} className={field.className} style={{whiteSpace:'pre-wrap'}}><strong>{field.label}: </strong>{String(row[field.name]??'')}</p>)}
 <div style={{display:'flex',gap:10}}><span><button className={config.classes.edit} data-testid={config.uiNamespace+"-edit"} data-record-id={String(row[config.pk])} aria-label={actionLabel('edit',row)} onClick={()=>{setEditing(row[config.pk] as string|number);setValues(Object.fromEntries(config.fields.map(field=>[field.name,String(row[field.name]??'')])));}}>Edit this record</button></span><span><button className={config.classes.delete} data-testid={config.uiNamespace+"-delete"} data-record-id={String(row[config.pk])} aria-label={actionLabel('delete',row)} disabled={busy} onClick={()=>void run('delete',row)}>Delete this record</button></span></div>
 </article>)}</section>
 </main>;
}
'''
