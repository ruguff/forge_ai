import {useState} from 'react';
import {api} from './Identity';
import contract from './ui-contract.json';
type Order={id:number;state:string;simulation:{id:number;state:string;amount_minor:number;currency:string}|null;refunds:{id:number;state:string}[]};
type Attempt={path:string;body:Record<string,string|number>};
const ids=contract.payments.ids;
export default function Payments({order,admin,reload}:{order:Order;admin:boolean;reload:()=>Promise<void>}){
 const storage='simulation-request-'+order.id;
 const [busy,setBusy]=useState(false),[message,setMessage]=useState(''),[error,setError]=useState(false);
 const [pending,setPending]=useState<Attempt|null>(()=>{try{return JSON.parse(sessionStorage.getItem(storage)??'null');}catch{return null;}});
 async function send(attempt:Attempt){
  if(busy)return;setBusy(true);setMessage('');setError(false);
  try{
   // The fixed API prefixes prevent a tampered local retry from selecting another API.
   if(!/^\/api\/(admin\/)?simulation\//.test(attempt.path))throw new Error('Invalid saved simulation request');
   sessionStorage.setItem(storage,JSON.stringify(attempt));setPending(attempt);
   const result=await api(attempt.path,'POST',attempt.body);
   sessionStorage.removeItem(storage);setPending(null);
   await reload();setMessage('Simulated result: '+result.state+'. No real money moved.');
  }catch(e){setError(true);setMessage((e instanceof Error?e.message:'Request failed')+' Refresh to inspect saved state, or retry the same request.');}
  finally{setBusy(false);}
 }
 function action(path:string,body:Record<string,string|number>={}){void send({path,body:{...body,idempotency_key:crypto.randomUUID()}});}
 const p=order.simulation,refund=order.refunds.find(r=>r.state==='pending');
 return <section className="payment-panel" data-testid={ids.panel+'-'+order.id} aria-label={'Payment simulator for order '+order.id}>
  <p className="payment-notice" data-testid={ids.notice}>OFFLINE PAYMENT SIMULATOR · No real money</p>
  <p data-testid={ids.status}>Simulation: {p?.state??'not started'}{refund?' · Refund pending':''}</p>
  <p>These controls generate test outcomes. They do not contact a bank or payment provider.</p>
  {message&&<p role={error?'alert':'status'}>{message}</p>}
  {pending?<div className="order-actions"><button disabled={busy} onClick={()=>void send(pending)}>Retry saved simulation request</button><button disabled={busy} onClick={()=>{sessionStorage.removeItem(storage);setPending(null);}}>Discard saved request after checking status</button></div>:<div className="order-actions">
   {!admin&&!p&&order.state==='awaiting_payment'&&<button disabled={busy} onClick={()=>action('/api/simulation/orders/'+order.id+'/payment')}>Start simulated payment</button>}
   {!admin&&p?.state==='pending'&&['succeeded','failed','cancelled'].map(outcome=><button key={outcome} disabled={busy} onClick={()=>action('/api/simulation/payments/'+p.id+'/resolve',{outcome,amount_minor:p.amount_minor,currency:p.currency})}>Simulate {outcome==='succeeded'?'success':outcome==='failed'?'failure':'cancellation'}</button>)}
   {admin&&p?.state==='succeeded'&&!refund&&<button disabled={busy} onClick={()=>action('/api/admin/simulation/payments/'+p.id+'/refund')}>Start full simulated refund</button>}
   {admin&&refund&&['succeeded','failed'].map(outcome=><button key={outcome} disabled={busy} onClick={()=>action('/api/admin/simulation/refunds/'+refund.id+'/resolve',{outcome})}>Simulate refund {outcome==='succeeded'?'success':'failure'}</button>)}
  </div>}
  {order.refunds.length>0&&<p>Refund history: {order.refunds.map(r=>'#'+r.id+' '+r.state).join(', ')}</p>}
 </section>;
}
