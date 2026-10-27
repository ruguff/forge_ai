import {useState} from 'react';
import {api} from './Identity';
import contract from './ui-contract.json';
type Order={fulfillment?:{status:string};id:number;state:string;payment_status:string;provider_payment:{state:string}|null;provider_refunds:{id:number;state:string}[]};
type Callback={razorpay_order_id:string;razorpay_payment_id:string;razorpay_signature:string};
type CheckoutOptions={key:string;order_id:string;amount:number;currency:string;name:string;handler:(value:Callback)=>void;modal:{ondismiss:()=>void}};
declare global {interface Window {Razorpay?:new(options:CheckoutOptions)=>{open:()=>void}}}
let loading:Promise<void>|undefined;
function loadCheckout(){
 if(window.Razorpay)return Promise.resolve();
 if(!loading)loading=new Promise<void>((resolve,reject)=>{
  const script=document.createElement('script');script.src='https://checkout.razorpay.com/v1/checkout.js';script.async=true;
  const timer=setTimeout(()=>{script.remove();loading=undefined;reject(new Error('Checkout timed out. Reconcile the saved order before retrying.'));},15000);
  script.onload=()=>{clearTimeout(timer);if(window.Razorpay)resolve();else{loading=undefined;reject(new Error('Provider Checkout unavailable'));}};
  script.onerror=()=>{clearTimeout(timer);script.remove();loading=undefined;reject(new Error('Provider Checkout needs internet access.'));};document.head.appendChild(script);
 });return loading;
}
export default function RazorpayCheckout({order,admin,reload}:{order:Order;admin:boolean;reload:()=>Promise<void>}){
 const [busy,setBusy]=useState(false),[message,setMessage]=useState(''),[error,setError]=useState(false);
 const storage='razorpay-refund-'+order.id;
 async function run(work:()=>Promise<void>){if(busy)return;setBusy(true);setMessage('');setError(false);try{await work();await reload();}catch(e){setError(true);setMessage(e instanceof Error?e.message:'Provider request failed');}finally{setBusy(false);}}
 async function refresh(){await api('/api/'+(admin?'admin/':'')+'razorpay/orders/'+order.id+'/reconcile','POST');setMessage('Saved provider state refreshed.');}
 async function checkout(){
  const options=await api('/api/razorpay/orders/'+order.id+'/checkout','POST');
  await loadCheckout();
  const widget=new window.Razorpay!({...options,handler:(value:Callback)=>{void run(async()=>{
   await api('/api/razorpay/orders/'+order.id+'/verify','POST',value);setMessage('Provider evidence checked. See saved status below.');
  });},modal:{ondismiss:()=>setMessage('Checkout closed. Payment is not confirmed by closing this window. Refresh provider status.')}});
  widget.open();setMessage('Test checkout opened. Payment is confirmed only after server verification.');
 }
 async function refund(){
  if(order.provider_refunds.some(r=>r.state==='creating')){
   await api('/api/admin/razorpay/orders/'+order.id+'/retry-refund','POST');
   setMessage('Saved refund request retried with its original provider key. Refresh provider status.');return;
  }
  let key=sessionStorage.getItem(storage);if(!key){key=crypto.randomUUID();sessionStorage.setItem(storage,key);}
  const value=await api('/api/admin/razorpay/orders/'+order.id+'/refund','POST',{idempotency_key:key});
  // Only a definite failed/processed response releases the retry key.
  if(value.provider_refunds.some((r:{state:string})=>r.state==='processed')||value.provider_refunds.slice(-1)[0]?.state==='failed')sessionStorage.removeItem(storage);
  setMessage('Refund request recorded. Refresh provider status for the final result.');
 }
 return <section className="payment-panel" data-testid={contract.payments.ids.panel+'-'+order.id} aria-label={'Razorpay test payment for order '+order.id}>
  <p className="payment-notice" data-testid={contract.payments.ids.notice}>RAZORPAY TEST MODE · No live payments</p>
  <p data-testid={contract.payments.ids.status}>Provider status: {order.payment_status}</p>
  <p>Test credentials and internet are required. Checkout is provided by Razorpay. Do not enter real card details.</p>
  {['late_capture','review'].includes(order.payment_status)&&<p role="alert">Administrator review required. This order must not be fulfilled.</p>}
  {message&&<p role={error?'alert':'status'}>{message}</p>}
  <div className="order-actions">
   {!admin&&order.state==='awaiting_payment'&&<button disabled={busy} onClick={()=>void run(checkout)}>Open Razorpay test checkout</button>}
   {order.provider_payment&&<button disabled={busy} onClick={()=>void run(refresh)}>Refresh provider status</button>}
   {admin&&(!order.fulfillment||order.fulfillment.status==='not_packed')&&(['captured','late_capture'].includes(order.payment_status)||order.provider_refunds.some(r=>r.state==='creating'))&&<button disabled={busy} onClick={()=>void run(refund)}>Request or retry full test refund</button>}
  </div>
  {order.provider_refunds.length>0&&<p>Refunds: {order.provider_refunds.map(r=>'#'+r.id+' '+r.state).join(', ')}</p>}
 </section>;
}
