import {ShipmentTracking} from './Fulfillment';
import Orders,{AddToCart} from './Orders';
import Identity from './Identity';
import {FormEvent, useEffect, useRef, useState} from 'react';
import contract from './ui-contract.json';
import './styles.css';

type Image = {url:string;alt:string};
type Product = {id:number;slug:string;name:string;material:string;category:string;category_slug:string;price_minor:number;max_price_minor:number;currency:string;available:boolean;images:Image[]};
type Variant = {id:number;sku:string;label:string;options:Record<string,string>;price_minor:number;currency:string;available:boolean};
type Detail = Omit<Product,'price_minor'|'max_price_minor'|'available'> & {description:string;variants:Variant[]};
type Category = {slug:string;name:string;count:number};
type Store = {name:string;tagline:string;currency:string};
type Result = {items:Product[];total:number;page:number;limit:number};
type Filters = {q:string;category:string;min:string;max:string;stock:boolean;sort:string};
const emptyFilters:Filters = {q:'',category:'',min:'',max:'',stock:false,sort:'featured'};
const ids = contract.ids;
const money = (value:number,currency:string) => new Intl.NumberFormat('en-IN',{style:'currency',currency,maximumFractionDigits:value%100?2:0}).format(value/100);
const productPath = (slug:string) => '/products/'+encodeURIComponent(slug);
const productSlug = (path:string) => {if(!path.startsWith('/products/'))return null;try{return decodeURIComponent(path.slice('/products/'.length));}catch{return 'invalid-product-path';}};

function Icon({name}:{name:'arrow'|'search'|'plus'|'minus'|'leaf'|'close'}){
 const paths = {arrow:'M4 12h16m-6-6 6 6-6 6',search:'m20 20-5-5M17 10a7 7 0 1 1-14 0 7 7 0 0 1 14 0',plus:'M12 5v14M5 12h14',minus:'M5 12h14',leaf:'M20 4C9 3 3 9 6 16c7 5 14-1 14-12ZM6 19 16 9',close:'m6 6 12 12M6 18 18 6'};
 return <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d={paths[name]}/></svg>;
}

async function getJSON<T>(path:string,signal?:AbortSignal):Promise<T>{
 const response=await fetch(path,{signal});
 if(!response.ok) throw new Error(response.status===404?'This product is not available.':'We could not load the catalogue. Please try again.');
 return response.json() as Promise<T>;
}

function ProductImage({image,className=''}:{image:Image|undefined;className?:string}){
 const [failed,setFailed]=useState(false);
 useEffect(()=>setFailed(false),[image?.url]);
 return image&&!failed?<img className={className} src={image.url} alt={image.alt} loading="lazy" onError={()=>setFailed(true)}/>:<div className="image-fallback" role="img" aria-label="Product image unavailable"><Icon name="leaf"/><span>Image unavailable</span></div>;
}

export default function App(){
 const [store,setStore]=useState<Store|null>(null),[categories,setCategories]=useState<Category[]>([]);
 const [metadataError,setMetadataError]=useState(''),[metadataAttempt,setMetadataAttempt]=useState(0);
 const [path,setPath]=useState(window.location.pathname);
 const [draft,setDraft]=useState<Filters>(emptyFilters),[filters,setFilters]=useState<Filters>(emptyFilters);
 const [page,setPage]=useState(1),[result,setResult]=useState<Result|null>(null);
 const [loading,setLoading]=useState(true),[error,setError]=useState(''),[attempt,setAttempt]=useState(0),[filterOpen,setFilterOpen]=useState(false);
 const [detail,setDetail]=useState<Detail|null>(null),[detailBusy,setDetailBusy]=useState(false),[detailError,setDetailError]=useState('');
 const [sku,setSku]=useState(''),[imageIndex,setImageIndex]=useState(0);
 const heading=useRef<HTMLHeadingElement>(null),navigated=useRef(false);
 const slug=productSlug(path);
 useEffect(()=>{const handler=()=>{navigated.current=true;setPath(window.location.pathname);};window.addEventListener('popstate',handler);return()=>window.removeEventListener('popstate',handler);},[]);
 function navigate(next:string){window.history.pushState({},'',next);navigated.current=true;setPath(next);window.scrollTo({top:0,behavior:'instant'});}
 useEffect(()=>{const controller=new AbortController();setMetadataError('');Promise.all([getJSON<Store>('/api/store',controller.signal),getJSON<Category[]>('/api/categories',controller.signal)]).then(([s,c])=>{setStore(s);setCategories(c);}).catch(e=>{if(e.name!=='AbortError')setMetadataError(String(e.message));});return()=>controller.abort();},[metadataAttempt]);
 useEffect(()=>{
  if(slug)return;
  const controller=new AbortController();setLoading(true);setError('');setResult(null);
  const query=new URLSearchParams({q:filters.q,sort:filters.sort,page:String(page),limit:'6'});
  if(filters.category)query.set('category',filters.category);
  if(filters.min)query.set('min_price',String(Math.round(Number(filters.min)*100)));
  if(filters.max)query.set('max_price',String(Math.round(Number(filters.max)*100)));
  if(filters.stock)query.set('in_stock','true');
  getJSON<Result>('/api/products?'+query,controller.signal).then(setResult).catch(e=>{if(e.name!=='AbortError')setError(e.message);}).finally(()=>{if(!controller.signal.aborted)setLoading(false);});
  return()=>controller.abort();
 },[filters,page,attempt,slug]);
 useEffect(()=>{
  if(!slug){setDetail(null);return;}
  const controller=new AbortController();setDetail(null);setDetailBusy(true);setDetailError('');
  getJSON<Detail>('/api/products/'+encodeURIComponent(slug),controller.signal).then(data=>{setDetail(data);setSku((data.variants.find(v=>v.available)??data.variants[0]).sku);setImageIndex(0);}).catch(e=>{if(e.name!=='AbortError')setDetailError(e.message);}).finally(()=>{if(!controller.signal.aborted)setDetailBusy(false);});
  return()=>controller.abort();
 },[slug,attempt]);
 useEffect(()=>{if(navigated.current&&!detailBusy&&!loading){heading.current?.focus();navigated.current=false;}},[path,detailBusy,loading,detail]);
 useEffect(()=>{document.title=(detail?detail.name+' · ':'')+(store?.name??'Shop')+' — The everyday edit';},[detail,store]);
 const selected=detail?.variants.find(v=>v.sku===sku);
 function apply(event:FormEvent){event.preventDefault();setError('');const min=Number(draft.min),max=Number(draft.max);if((draft.min&&(!Number.isFinite(min)||min<0))||(draft.max&&(!Number.isFinite(max)||max<0))||(draft.min&&draft.max&&min>max)){setError('Enter a valid price range. Minimum price cannot exceed maximum price.');return;}setPage(1);setFilters({...draft,q:draft.q.trim()});}
 function clear(){setDraft(emptyFilters);setFilters(emptyFilters);setPage(1);setError('');}
 const activeCount=Number(!!filters.category)+Number(!!filters.min||!!filters.max)+Number(filters.stock);
 if(path.match(/^\/orders\/[^/]+\/tracking\/?$/))return <ShipmentTracking key={path} orderId={path.split('/')[2]}/>;
 if(path==='/cart'||path==='/orders'||path==='/admin/orders')return <Orders/>;
 if(path.startsWith('/account')||path==='/admin')return <Identity/>;
 return <>
  <a className="skip-link" href="#main">Skip to main content</a>
  <div className="announcement">THE EVERYDAY EDIT <span>Thoughtful things for life outside.</span></div>
  <header className="site-header shell"><a className="brand" href="/" onClick={e=>{e.preventDefault();navigate('/');}} aria-label={(store?.name??'Store')+' home'}><span className="brand-mark" aria-hidden="true"><Icon name="leaf"/></span>{store?.name??'The shop'}<span className="brand-dot">®</span></a><nav aria-label="Main navigation"><a href="/" aria-current={!slug?'page':undefined} onClick={e=>{e.preventDefault();navigate('/');}}>The collection</a><a href="/cart">Cart</a><a href="/orders">Orders</a><a href="/account">My account</a><a href="/admin">Administration</a></nav><span className="preview-badge">Catalogue preview</span></header>
  {metadataError&&<div className="metadata-error shell" role="alert">{metadataError}<button className="text-button" onClick={()=>setMetadataAttempt(n=>n+1)}>Reload store details</button></div>}
  <main id="main" tabIndex={-1}>
   {!slug?<>
    <section className="hero shell" aria-labelledby="hero-heading"><div className="hero-copy"><span className="eyebrow"><i/> CONSIDERED ESSENTIALS</span><h1 id="hero-heading" ref={heading} tabIndex={-1}>Less stuff.<br/><em>More living.</em></h1><p>{store?.tagline??'Considered essentials. Everyday adventures.'}</p><a className="button button-dark" href="#collection">Explore the collection <Icon name="arrow"/></a><div className="hero-note"><span className="mini-line"/> Useful by nature. Simple by design.</div></div><div className="hero-art" role="img" aria-label="Illustrated backpack, bottle and lantern from the everyday collection"><span className="sun-disc"/><span className="art-label">THE ART OF<br/>GOING LIGHT.</span><img className="art-pack" src="/assets/pack.svg" alt=""/><img className="art-bottle" src="/assets/bottle.svg" alt=""/><img className="art-lamp" src="/assets/lamp.svg" alt=""/><span className="art-caption">A little less. A little better.</span></div></section>
    <div className="values-strip shell"><span><Icon name="leaf"/> Practical by design</span><span>Everyday versatility</span><span>Room for the outdoors</span><span className="strip-end">THE COLLECTION / 01</span></div>
    <section className="collection shell" id="collection" aria-labelledby="collection-heading"><div className="collection-heading"><div><span className="eyebrow">THE EVERYDAY COLLECTION</span><h2 id="collection-heading">Good things, built to stay.</h2></div><span className="collection-aside">For wherever the day takes you.</span></div>
     <div className="catalogue-layout"><aside className="filters" aria-label="Product filters"><div className="filter-title"><h3>Refine your search</h3><button className="text-button" data-testid={ids.clear} onClick={clear}>Reset</button></div><button className="mobile-filter-toggle" aria-expanded={filterOpen} aria-controls="filter-form" onClick={()=>setFilterOpen(!filterOpen)}>Filters {activeCount?`(${activeCount})`:''}<Icon name={filterOpen?'minus':'plus'}/></button><form id="filter-form" className={'filter-form '+(filterOpen?'is-open':'')} onSubmit={apply}>
      <fieldset><legend>Category</legend><label className="sr-only" htmlFor="category">Choose category</label><select id="category" data-testid={ids.category} value={draft.category} onChange={e=>setDraft({...draft,category:e.target.value})}><option value="">All essentials</option>{categories.map(c=><option value={c.slug} key={c.slug}>{c.name} ({c.count})</option>)}</select></fieldset>
      <fieldset><legend>Price range <span>({store?.currency??'…'})</span></legend><div className="price-inputs"><label htmlFor="min-price"><span>From</span><input id="min-price" data-testid={ids['min-price']} type="number" min="0" max="20000000" step="0.01" placeholder="0" value={draft.min} onChange={e=>setDraft({...draft,min:e.target.value})}/></label><span aria-hidden="true">—</span><label htmlFor="max-price"><span>To</span><input id="max-price" data-testid={ids['max-price']} type="number" min="0" max="20000000" step="0.01" placeholder="Any" value={draft.max} onChange={e=>setDraft({...draft,max:e.target.value})}/></label></div></fieldset>
      <fieldset><legend>Availability</legend><label className="checkbox-label"><input type="checkbox" data-testid={ids.stock} checked={draft.stock} onChange={e=>setDraft({...draft,stock:e.target.checked})}/> In stock only</label></fieldset>
      <button className="button button-outline apply-filters" data-testid={ids.apply} type="submit">Apply filters <Icon name="arrow"/></button><div className="filter-note"><Icon name="leaf"/><p>A smaller collection.<br/>More considered choices.</p></div>
     </form></aside>
     <div className="product-section"><div className="catalogue-toolbar"><label className="search-box"><span className="sr-only">Search products</span><Icon name="search"/><input form="filter-form" data-testid={ids.search} type="search" placeholder="Find your everyday essential…" value={draft.q} onChange={e=>setDraft({...draft,q:e.target.value})}/></label><label className="sort-label"><span>Sort by</span><select data-testid={ids.sort} value={filters.sort} onChange={e=>{setPage(1);setFilters({...filters,sort:e.target.value});setDraft({...draft,sort:e.target.value});}}><option value="featured">Featured</option><option value="price-asc">Price: low to high</option><option value="price-desc">Price: high to low</option><option value="name">Name</option></select></label></div>
      <div className="results-meta"><p role="status" aria-live="polite" data-testid={ids.results}>{loading?'Finding your essentials…':result?`${result.total} ${result.total===1?'essential':'essentials'}${filters.q?` for “${filters.q}”`:''}`:'Catalogue unavailable'}</p>{activeCount>0&&<span>{activeCount} {activeCount===1?'filter':'filters'} applied</span>}</div>
      {error&&<div className="state-box error-state" role="alert" data-testid={ids.error}><h3>A small pause.</h3><p>{error}</p><button className="button button-outline" data-testid={ids.retry} onClick={()=>setAttempt(n=>n+1)}>Try again</button></div>}
      {loading&&<div className="product-grid skeleton-grid" role="status" aria-label="Loading products" data-testid={ids.loading}>{[0,1,2,3,4,5].map(i=><div className="skeleton-card" key={i}><div/><span/><span/></div>)}</div>}
      {!loading&&!error&&result?.items.length===0&&<div className="state-box" data-testid={ids.empty}><Icon name="search"/><h3>Nothing here just yet.</h3><p>Try another search or give your filters a little more room.</p><button className="button button-outline" onClick={clear}>Clear search and filters</button></div>}
      {!loading&&!error&&result&&result.items.length>0&&<><div className="product-grid">{result.items.map((p,index)=><article className="product-card" key={p.slug} data-testid={ids.product} data-product-slug={p.slug}><a className="product-link" href={productPath(p.slug)} onClick={e=>{e.preventDefault();navigate(productPath(p.slug));}}><div className={'product-visual tone-'+index%4}><ProductImage image={p.images[0]}/>{!p.available&&<span className="stock-badge">Out of stock</span>}<span className="view-product" aria-hidden="true"><Icon name="arrow"/></span></div><div className="product-copy"><span className="product-category">{p.category}</span><div className="product-name-price"><h3>{p.name}</h3><span className="card-price">{p.max_price_minor!==p.price_minor&&<small>From </small>}{money(p.price_minor,p.currency)}</span></div><p>{p.material}</p><span className="sr-only">View product details</span></div></a></article>)}</div><nav className="pagination" aria-label="Product pages"><span>Page {page} of {Math.max(1,Math.ceil(result.total/result.limit))}</span><div><button className="button button-outline" data-testid={ids.previous} disabled={page<=1} onClick={()=>setPage(n=>n-1)}>Previous</button><button className="button button-outline" data-testid={ids.next} disabled={page*result.limit>=result.total} onClick={()=>setPage(n=>n+1)}>Next <Icon name="arrow"/></button></div></nav></>}
     </div></div>
    </section>
   </>:<section className="detail shell" data-testid={ids.detail}><a className="back-link" href="/" data-testid={ids.back} onClick={e=>{e.preventDefault();navigate('/');}}>← Back to the collection</a>{detailBusy&&<div className="state-box" role="status" data-testid={ids.loading}>Loading product details…</div>}{detailError&&<div className="state-box error-state" role="alert" data-testid={ids.error}><h1 ref={heading} tabIndex={-1}>Product unavailable</h1><p>{detailError}</p><button className="button button-outline" data-testid={ids.retry} onClick={()=>setAttempt(n=>n+1)}>Try again</button></div>}{detail&&selected&&<div className="detail-grid"><div className="gallery" data-testid={ids.gallery}><div className="detail-image"><ProductImage image={detail.images[imageIndex]}/></div><div className="thumbnails" aria-label="Product images">{detail.images.map((image,i)=><button key={image.url+i} aria-label={'View image '+(i+1)} aria-pressed={imageIndex===i} onClick={()=>setImageIndex(i)}><ProductImage image={image}/></button>)}</div></div><div className="detail-copy"><span className="eyebrow">{detail.category}</span><h1 ref={heading} tabIndex={-1}>{detail.name}</h1><p className="detail-material">{detail.material}</p><p className="detail-price" data-testid={ids.price}>{money(selected.price_minor,selected.currency)}</p><p className="detail-description">{detail.description}</p><label className="variant-label" htmlFor="variant">Choose your variant</label><select id="variant" data-testid={ids.variant} value={sku} onChange={e=>setSku(e.target.value)}>{detail.variants.map(v=><option key={v.sku} value={v.sku}>{v.label}{!v.available?' — Out of stock':''}</option>)}</select><dl className="variant-facts"><div><dt>SKU</dt><dd data-testid={ids.sku}>{selected.sku}</dd></div>{Object.entries(selected.options).map(([key,value])=><div key={key}><dt>{key}</dt><dd>{value}</dd></div>)}</dl><p className={'availability '+(selected.available?'available':'unavailable')} data-testid={ids.availability}><span/>{selected.available?'In stock':'Out of stock'}</p><AddToCart sku={selected.sku}/><div className="catalogue-notice"><Icon name="leaf"/><p>You’re exploring our catalogue preview.<br/>Create an unpaid order from your cart. Offline payment simulation only. No real money is collected.</p></div></div></div>}</section>}
  </main>
  <section className="approach shell" id="approach"><Icon name="leaf"/><div><span className="eyebrow">A MORE CONSIDERED EVERYDAY</span><h2>Take what matters.<br/><em>Leave room for more.</em></h2></div><p>Explore a focused collection of practical essentials for the everyday and the outside. Find the details, choose your variant, and make a little room for a slower pace.</p></section>
  <footer className="site-footer shell"><span className="footer-brand">{store?.name??'The shop'}<sup>®</sup></span><p>Catalogue preview · Online checkout is not enabled.</p><a href="#main">Back to top ↑</a></footer>
 </>;
}
