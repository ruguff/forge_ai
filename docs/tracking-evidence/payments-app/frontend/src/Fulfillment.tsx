import {useEffect,useState,type FormEvent} from 'react';
import {api} from './Identity';
import contract from './ui-contract.json';

const ids=contract.delivery.ids;

type ShippingDetails={courier_name:string;tracking_number:string;version:number;updated_at:number};
export type Delivery = {status:string;next_status:string|null;updated_at:number|null;demo_only:boolean;shipping_details:ShippingDetails|null;can_edit_shipping:boolean};
export default function Fulfillment({order,admin,reload}:{order:{id:number;fulfillment?:Delivery};admin:boolean;reload:()=>Promise<void>}){
 const [busy,setBusy]=useState<'shipping'|'status'|'refresh'|null>(null),[error,setError]=useState(''),[message,setMessage]=useState('');
 const delivery=order.fulfillment,shipping=delivery?.shipping_details;
 const [courier,setCourier]=useState(shipping?.courier_name??''),[tracking,setTracking]=useState(shipping?.tracking_number??'');
 useEffect(()=>{setCourier(shipping?.courier_name??'');setTracking(shipping?.tracking_number??'');},[order.id,shipping?.version,shipping?.courier_name,shipping?.tracking_number]);
 if(!delivery)return null;
 const labels:Record<string,string>={not_packed:'Not packed',packed:'Packed',shipped:'Shipped',delivered:'Delivered'};
 async function advance(){
  if(busy||!delivery?.next_status)return;
  setBusy('status');setError('');setMessage('');
  try{
   await api(`/api/admin/orders/${order.id}/fulfillment`,'POST',{expected_status:delivery.status,status:delivery.next_status});
   await reload();
  }catch(e){setError(e instanceof Error?e.message:'Unable to update delivery. Refresh and retry.');}
  finally{setBusy(null);}
 }
 async function saveShipping(event:FormEvent<HTMLFormElement>){
  event.preventDefault();if(busy)return;
  if(!courier.trim()||!tracking.trim()){setError('Enter both the courier name and tracking number.');return;}
  setBusy('shipping');setError('');setMessage('');
  try{
   await api(`/api/admin/orders/${order.id}/shipping-details`,'POST',{expected_version:shipping?.version??0,courier_name:courier.trim(),tracking_number:tracking.trim()});
   await reload();setMessage('Courier and tracking number saved.');
  }catch(e){setError(e instanceof Error?e.message:'Unable to save shipping details.');}
  finally{setBusy(null);}
 }
 async function refresh(){
  if(busy)return;setBusy('refresh');setError('');setMessage('');
  try{await reload();}catch(e){setError(e instanceof Error?e.message:'Unable to refresh order.');}finally{setBusy(null);}
 }
 return <section className="payment-panel" style={{minWidth:0,boxSizing:'border-box',maxWidth:'100%'}} aria-label={`Delivery for order ${order.id}`}>
  <h4>Delivery status</h4>
  <p role="status" data-testid={`${ids.status}-${order.id}`}>{labels[delivery.status]??delivery.status}</p>
  <p>Delivery updates and tracking details are entered by the store. Courier updates are not automatic.</p>
  {delivery.updated_at&&<p>Updated {new Date(delivery.updated_at*1000).toLocaleString()}</p>}
  <div data-testid={`${ids.details}-${order.id}`}>
   {shipping?<><p><strong>Courier:</strong> {shipping.courier_name}</p><p><strong>Tracking number:</strong> <span style={{overflowWrap:'anywhere'}}>{shipping.tracking_number}</span></p></>:<p>Courier and tracking number have not been added yet.</p>}
  </div>
  {admin&&delivery.can_edit_shipping&&<form onSubmit={event=>void saveShipping(event)} data-testid={`${ids.form}-${order.id}`} aria-label={`Shipping details for order ${order.id}`}>
   <fieldset disabled={busy!==null}>
    <legend>{shipping?'Edit shipping details':'Add shipping details'}</legend>
    <label htmlFor={`courier-${order.id}`}>Courier name<input id={`courier-${order.id}`} value={courier} onChange={e=>setCourier(e.target.value)} maxLength={100} required style={{maxWidth:'none'}} autoComplete="off"/></label>
    <label htmlFor={`tracking-${order.id}`}>Tracking number<input id={`tracking-${order.id}`} value={tracking} onChange={e=>setTracking(e.target.value)} maxLength={100} required style={{maxWidth:'none'}} autoComplete="off" spellCheck={false}/></label>
    <small>Enter both values exactly as supplied by the courier. Saving does not change delivery status.</small>
    <button type="submit">{busy==='shipping'?'Saving shipping details…':`Save shipping details for order #${order.id}`}</button>
   </fieldset>
  </form>}
  {admin&&delivery.status==='delivered'&&<p>Shipping details are read-only after delivery.</p>}
  {admin&&delivery.next_status&&<div className="order-actions"><button disabled={busy!==null} onClick={()=>void advance()}>{busy==='status'?'Saving…':`Mark order #${order.id} as ${labels[delivery.next_status].toLowerCase()}`}</button></div>}
  {admin&&!delivery.next_status&&delivery.status!=='delivered'&&<p>Delivery and shipping updates require a paid order with no active refund.</p>}
  {message&&<p role="status">{message}</p>}
  {error&&<><p role="alert">{error}</p><button disabled={busy!==null} onClick={()=>void refresh()}>Refresh order #{order.id}</button></>}
 </section>;
}
