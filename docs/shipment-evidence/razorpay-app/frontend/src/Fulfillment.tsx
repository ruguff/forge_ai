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
  {!admin&&<p><a href={`/orders/${order.id}/tracking`} data-testid={`${ids.track}-${order.id}`}>Track shipment for order #{order.id}</a></p>}
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

type Shipment={order_id:number;availability:string;status:string;updated_at:number|null;shipping_details:ShippingDetails|null;history:{status:string;recorded_at:number}[];update_source:'store_manual';estimated_delivery:null};
const steps=[{key:'placed',label:'Order placed'},{key:'packed',label:'Packed'},{key:'shipped',label:'Shipped'},{key:'delivered',label:'Delivered'}];
const statusText:Record<string,string>={not_packed:'Awaiting packing',packed:'Packed — awaiting dispatch',shipped:'Shipped',delivered:'Delivered'};
const stopped:Record<string,{title:string;message:string}>={
 awaiting_payment:{title:'Awaiting payment',message:'Shipment preparation is pending payment.'},
 cancelled:{title:'Order cancelled',message:'This order is cancelled. No shipment is in progress.'},
 expired:{title:'Order expired',message:'The unpaid reservation expired. No shipment is in progress.'},
 refunded:{title:'Order refunded',message:'This order has been refunded. No shipment is in progress.'},
 on_hold:{title:'Shipment on hold',message:'Shipment updates are paused. Check your order history for payment or refund details.'}
};

export function ShipmentTracking({orderId}:{orderId:string}){
 const [shipment,setShipment]=useState<Shipment|null>(null),[loading,setLoading]=useState(true),[error,setError]=useState('');
 const [attempt,setAttempt]=useState(0),[checkedAt,setCheckedAt]=useState<Date|null>(null),[copyMessage,setCopyMessage]=useState('');
 useEffect(()=>{
  const controller=new AbortController();setLoading(true);setError('');setShipment(null);setCheckedAt(null);setCopyMessage('');
  async function load(){
   if(!/^[1-9][0-9]*$/.test(orderId)||Number(orderId)>2147483647)throw new Error('This shipment link is invalid. Open a shipment from your order history.');
   const response=await fetch(`/api/orders/${orderId}/shipment`,{credentials:'same-origin',cache:'no-store',signal:controller.signal});
   if(response.status===401||response.status===403)throw new Error('Sign in with the account that placed this order to view its shipment.');
   if(response.status===404)throw new Error('Shipment not found for your account. Check your order history.');
   if(!response.ok)throw new Error('Shipment details are unavailable. Please try again.');
   const data:Shipment=await response.json();
   if(!controller.signal.aborted){setShipment(data);setCheckedAt(new Date());}
  }
  void load().catch(e=>{if(!controller.signal.aborted)setError(e instanceof Error?e.message:'Unable to load shipment.');}).finally(()=>{if(!controller.signal.aborted)setLoading(false);});
  return()=>controller.abort();
 },[orderId,attempt]);
 async function copyTracking(){
  if(!shipment?.shipping_details)return;
  try{await navigator.clipboard.writeText(shipment.shipping_details.tracking_number);setCopyMessage('Tracking number copied.');}
  catch{setCopyMessage('Copy is unavailable. Select and copy the tracking number shown above.');}
 }
 const hold=shipment?stopped[shipment.availability]:undefined;
 const current=shipment?Math.max(0,steps.findIndex(step=>step.key===shipment.status)):0;
 return <div className="identity-page shipment-page">
  <header className="identity-header"><a className="brand" href="/">The collection ↗</a><nav aria-label="Store navigation"><a href="/">Shop</a><a href="/orders">My orders</a><a href="/account">Account</a></nav></header>
  <main className="identity-main shipment-main" data-testid={ids.page}>
   <a href="/orders">← Back to my orders</a><p className="eyebrow">YOUR DELIVERY</p><h1>Track your shipment</h1>
   <p className="identity-intro">View the delivery updates recorded by the store for your order.</p>
   {loading&&<p role="status" className="identity-message">Loading shipment…</p>}
   {error&&<section className="identity-card"><p role="alert">{error}</p><div className="order-actions"><button onClick={()=>setAttempt(v=>v+1)}>Try again</button><a href="/account">Sign in</a><a href="/orders">View my orders</a></div></section>}
   {shipment&&!loading&&<>
    <section className="identity-card shipment-summary" aria-label="Shipment overview">
     <div><p className="eyebrow">ORDER #{shipment.order_id}</p><h2 role="status" data-testid={ids.summary}>{hold?.title??statusText[shipment.status]??'Status unavailable'}</h2>
      <p>{hold?.message??(shipment.status==='delivered'?'The store has marked your order as delivered.':shipment.status==='shipped'?'The store has marked your order as shipped.':'The store has not marked this order as shipped yet.')}</p></div>
     <div><button className="button" onClick={()=>setAttempt(v=>v+1)}>Refresh shipment</button>{checkedAt&&<small>Last checked {checkedAt.toLocaleTimeString()}</small>}</div>
    </section>
    <div className="shipment-grid">
     <section className="identity-card" aria-labelledby="shipment-timeline-title"><h2 id="shipment-timeline-title">Delivery timeline</h2>
      <ol className="shipment-timeline" aria-label="Delivery timeline" data-testid={ids.timeline}>{steps.map((step,index)=>{
       const event=shipment.history.find(item=>item.status===step.key),completed=index<=current;
       return <li key={step.key} data-state={completed?'recorded':'pending'} aria-current={!hold&&index===current?'step':undefined}>
        <span className="shipment-step" aria-hidden="true">{completed?'✓':index+1}</span><div><h3>{step.label}</h3>
         {event?<time dateTime={new Date(event.recorded_at*1000).toISOString()}>{new Date(event.recorded_at*1000).toLocaleString()}</time>:<p>{completed?'Time not recorded':hold?'Not reached':'Pending store update'}</p>}
        </div></li>;
      })}</ol>
     </section>
     <section className="identity-card" aria-labelledby="shipment-courier-title"><h2 id="shipment-courier-title">Courier details</h2>
      {shipment.shipping_details?<><dl className="shipment-details"><dt>Courier</dt><dd>{shipment.shipping_details.courier_name}</dd><dt>Tracking number</dt><dd data-testid={ids.number}>{shipment.shipping_details.tracking_number}</dd></dl>
       <button onClick={()=>void copyTracking()}>Copy tracking number</button><p role="status">{copyMessage}</p></>:<p data-testid={ids.empty}>The store has not added courier details yet. Refresh this page after the store updates your order.</p>}
      <p className="shipment-notice">Updates are entered manually by the store. This page does not show live courier locations or automatic carrier scans.</p>
      <p>Estimated delivery has not been provided.</p>
     </section>
    </div>
   </>}
  </main>
 </div>;
}
