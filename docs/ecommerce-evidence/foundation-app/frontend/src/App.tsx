import {useEffect,useState} from 'react';
const config = {"title": "Foundation Task Manager", "fields": [{"name": "title", "label": "Title", "id": "title-input", "className": "record-title", "multiline": false, "numeric": false}, {"name": "description", "label": "Description", "id": "description-input", "className": "record-description", "multiline": true, "numeric": false}], "pk": "id", "buttons": {"create": "create-record-btn", "edit": "edit-record-btn", "delete": "delete-record-btn"}, "classes": {"list": "record-list", "item": "record-item", "edit": "edit-record", "delete": "delete-record", "create": "create-record", "save": "save-record"}, "rowAttributes": [], "actionLabels": {}, "api": {"list": "/api/tasks", "create": "/api/tasks", "edit": "/api/tasks/{task_id}", "delete": "/api/tasks/{task_id}"}, "updateMethod": "PUT", "uiNamespace": "tasks"};
type Row = Record<string,string|number|boolean|null>;
type Values = Record<string,string>;
export default function App(){
 const [rows,setRows]=useState<Row[]>([]),[values,setValues]=useState<Values>({}),[editing,setEditing]=useState<string|number|null>(null),[busy,setBusy]=useState(false),[error,setError]=useState('');
 const [loading,setLoading]=useState(true);
 const actionLabel=(action:'edit'|'delete',row:Row)=>{const labels:Record<string,string[]>=config.actionLabels;const label=labels[action];return label?label[0]+String(row[config.pk])+label[1]:undefined;};
 const url=(pattern:string,id:string|number)=>pattern.replace(/\{[^}]+\}/,encodeURIComponent(String(id)));
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
