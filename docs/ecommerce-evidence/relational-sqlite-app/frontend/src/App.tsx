import {useState} from 'react';
import Entity0 from './Entity0';
import Entity1 from './Entity1';
const views = [{label:"Category",View:Entity0},{label:"Product",View:Entity1}];
export default function App(){const [selected,setSelected]=useState(0);const View=views[selected].View;
return <><nav aria-label="Entities" style={{display:'flex',gap:12,flexWrap:'wrap',padding:20}}>{views.map((v,i)=><button key={v.label} aria-pressed={i===selected} onClick={()=>setSelected(i)}>{v.label}</button>)}</nav><View key={selected}/></>;}
