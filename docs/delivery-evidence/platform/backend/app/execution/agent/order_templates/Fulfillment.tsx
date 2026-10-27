import {useState} from 'react';
import {api} from './Identity';

export type Delivery = {status:string;next_status:string|null;updated_at:number|null;demo_only:boolean};
export default function Fulfillment({order,admin,reload}:{order:{id:number;fulfillment?:Delivery};admin:boolean;reload:()=>Promise<void>}){
 const [busy,setBusy]=useState(false),[error,setError]=useState('');
 const delivery=order.fulfillment;
 if(!delivery)return null;
 const labels:Record<string,string>={not_packed:'Not packed',packed:'Packed',shipped:'Shipped',delivered:'Delivered'};
 async function advance(){
  if(busy||!delivery?.next_status)return;
  setBusy(true);setError('');
  try{
   await api(`/api/admin/orders/${order.id}/fulfillment`,'POST',{expected_status:delivery.status,status:delivery.next_status});
   await reload();
  }catch(e){setError(e instanceof Error?e.message:'Unable to update delivery. Refresh and retry.');}
  finally{setBusy(false);}
 }
 return <section className="payment-panel" aria-label={`Delivery for order ${order.id}`}>
  <h4>Delivery status</h4>
  <p role="status" data-testid={`delivery-status-${order.id}`}>{labels[delivery.status]??delivery.status}</p>
  <p>Manual demo tracking — no courier booking or real dispatch.</p>
  {delivery.updated_at&&<p>Updated {new Date(delivery.updated_at*1000).toLocaleString()}</p>}
  {admin&&delivery.next_status&&<button disabled={busy} onClick={()=>void advance()}>{busy?'Saving…':`Mark order #${order.id} as ${labels[delivery.next_status].toLowerCase()}`}</button>}
  {admin&&!delivery.next_status&&delivery.status!=='delivered'&&<p>Delivery updates require a paid order with no active refund.</p>}
  {error&&<p role="alert">{error}</p>}
 </section>;
}
