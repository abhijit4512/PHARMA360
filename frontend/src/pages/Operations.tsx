import React, {useState} from 'react';
import {ResponsiveContainer, AreaChart, Area, CartesianGrid, XAxis, YAxis, Tooltip, PieChart, Pie, Cell} from 'recharts';
import {useQuery, useMutation, useQueryClient} from '@tanstack/react-query';import {api} from '../lib/api';import {Boxes,ClipboardList,Wallet,Truck,Users,AlertTriangle,Bell,CheckCircle2,XCircle,Clock3,PackageCheck,Search,Filter,ArrowRight,RefreshCw} from 'lucide-react';
export function Inventory(){
  const qc=useQueryClient();
  const {data=[]}=useQuery<any[]>({queryKey:['inventory'],queryFn:async()=>(await api.get('/inventory')).data,refetchInterval:30000});
  const {data:products=[]}=useQuery<any[]>({queryKey:['products'],queryFn:async()=>(await api.get('/products')).data});
  const user=JSON.parse(localStorage.getItem('pharma360_user')||'{}');
  const inventoryOnly=user.role==='inventory_manager';
  const [tab, setTab] = useState('items');
  const [search, setSearch] = useState('');
  const [category, setCategory] = useState('all');
  const [status, setStatus] = useState('all');
  const [inventoryPage,setInventoryPage]=useState(1);
  const INVENTORY_PAGE_SIZE=10;
  const [addOpen,setAddOpen]=useState(false);
  const [form,setForm]=useState({product_id:'',batch_number:'',quantity:'',purchase_price:'',expiry_date:''});
  const [error,setError]=useState('');
  const [importMessage,setImportMessage]=useState('');
  const [importBusy,setImportBusy]=useState(false);
  const [importPharmacyId,setImportPharmacyId]=useState(String(user.pharmacy_id||''));
  const [replaceCatalog,setReplaceCatalog]=useState(false);
  const [replaceInventory,setReplaceInventory]=useState(false);
  const {data:stores=[]}=useQuery<any[]>({queryKey:['stores'],queryFn:async()=>(await api.get('/stores')).data,enabled:user.role==='super_admin'});
  const importCsv=async(kind:'products'|'batches',file:File)=>{
    if(!file.name.toLowerCase().endsWith('.csv')){setImportMessage('Please select a CSV file.');return;}
    if(kind==='batches'&&user.role==='super_admin'&&!importPharmacyId){setImportMessage('Select a pharmacy/store before importing batches.');return;}
    const previewText=await file.text();
    const previewLines=previewText.split(/\r?\n/).filter(line=>line.trim()).slice(0,4);
    const rowCount=Math.max(0,previewText.split(/\r?\n/).filter(line=>line.trim()).length-1);
    const preview=previewLines.slice(1).join('\n');
    const action=kind==='products'?(replaceCatalog?'REPLACE MODE: existing active catalog products will be deactivated; matching CSV SKUs will be updated/reactivated. Order history references are preserved.':'Products with matching SKU will be updated; new SKUs will be created.'):(replaceInventory?'REPLACE MODE: existing batches in the selected store will be removed before importing this CSV.':'Batches will be matched by store + product SKU + batch number. Existing matching batch stock will be replaced by CSV current stock, not added.');
    if(!window.confirm(`CSV import preview\n\nFile: ${file.name}\nRows: ${rowCount}\n\nSample rows:\n${preview}\n\n${action}\n\nContinue?`))return;
    const fd=new FormData();fd.append('file',file);
    fd.append('replace_existing',String(kind==='products'?replaceCatalog:replaceInventory));
    if(kind==='batches'&&user.role==='super_admin')fd.append('pharmacy_id',importPharmacyId);
    setImportBusy(true);setImportMessage('Importing CSV…');
    try{
      const {data:result}=await api.post(`/inventory/import/${kind}`,fd,{headers:{'Content-Type':'multipart/form-data'}});
      setImportMessage(`${result.message}${result.errors?.length?` Errors: ${result.errors.slice(0,5).join(' | ')}`:''}`);
      qc.invalidateQueries({queryKey:['products']});qc.invalidateQueries({queryKey:['inventory']});qc.invalidateQueries({queryKey:['summary']});
    }catch(e:any){setImportMessage(e.response?.data?.detail||'CSV import failed. Check the file format and backend logs.');}
    finally{setImportBusy(false);}
  };
  const add=useMutation({mutationFn:async()=>api.post('/inventory/batches',{product_id:Number(form.product_id),batch_number:form.batch_number,quantity:Number(form.quantity),purchase_price:Number(form.purchase_price),expiry_date:form.expiry_date||null}),onSuccess:()=>{qc.invalidateQueries({queryKey:['inventory']});setAddOpen(false);setForm({product_id:'',batch_number:'',quantity:'',purchase_price:'',expiry_date:''});setError('')}});
  const rows=data.map((b:any)=>({...b,category:b.category||products.find((p:any)=>p.id===b.product_id)?.category||'Other'}));
  const categories=Array.from(new Set(rows.map((b:any)=>b.category)));
  const low=rows.filter((b:any)=>b.quantity<=10);
  const soon=rows.filter((b:any)=>b.expiry_date&&new Date(b.expiry_date).getTime()<=Date.now()+30*86400000);
  
  const filtered = rows.filter(
  (b: any) =>
    (!search ||
      `${b.product} ${b.batch_number} ${b.product_id}`
        .toLowerCase()
        .includes(search.toLowerCase())) &&
    (category === 'all' || b.category === category) &&
    (
      status === 'all' ||
      (status === 'low' && b.quantity <= 10) ||
      (status === 'in' && b.quantity > 10) ||
      (status === 'expiring' && soon.includes(b))
    )
);

// Sort alphabetically
const tableRows = [...filtered].sort(
  (a: any, b: any) =>
    String(a.product || '').localeCompare(
      String(b.product || ''),
      undefined,
      { sensitivity: 'base' }
    )
);

// Pagination
const totalPages = Math.max(
  1,
  Math.ceil(tableRows.length / INVENTORY_PAGE_SIZE)
);

const safePage = Math.min(inventoryPage, totalPages);

const getPaginationPages = (currentPage: number, pages: number): (number | string)[] => {
  if (pages <= 7) return Array.from({ length: pages }, (_, i) => i + 1);
  if (currentPage <= 3) return [1, 2, 3, '…', pages - 1, pages];
  if (currentPage >= pages - 2) return [1, 2, '…', pages - 2, pages - 1, pages];
  return [1, '…', currentPage - 1, currentPage, currentPage + 1, '…', pages];
};

const pageStart =
  tableRows.length === 0
    ? 0
    : (safePage - 1) * INVENTORY_PAGE_SIZE + 1;

const pageEnd = Math.min(
  safePage * INVENTORY_PAGE_SIZE,
  tableRows.length
);

const pageRows = tableRows.slice(
  (safePage - 1) * INVENTORY_PAGE_SIZE,
  safePage * INVENTORY_PAGE_SIZE
);
  const totalUnits=rows.reduce((a:number,b:any)=>a+b.quantity,0);
  const totalValue=rows.reduce((a:number,b:any)=>a+b.quantity*b.purchase_price,0);
  const categoryData=categories.map((name:any)=>({name,value:rows.filter((b:any)=>b.category===name).reduce((a:number,b:any)=>a+b.quantity,0)}));
  const trendData=[{month:'Jan',restocked:120,dispensed:95},{month:'Feb',restocked:145,dispensed:108},{month:'Mar',restocked:115,dispensed:130},{month:'Apr',restocked:160,dispensed:118},{month:'May',restocked:132,dispensed:142},{month:'Jun',restocked:170,dispensed:150},{month:'Jul',restocked:150,dispensed:120},{month:'Aug',restocked:180,dispensed:160},{month:'Sep',restocked:205,dispensed:170},{month:'Oct',restocked:175,dispensed:145},{month:'Nov',restocked:220,dispensed:180},{month:'Dec',restocked:230,dispensed:195}];
  const exportCsv=()=>{const csv=['Product,SKU/ID,Category,Quantity,Batch,Expiry,Purchase Price',...rows.map((b:any)=>[b.product,b.product_id,b.category,b.quantity,b.batch_number,b.expiry_date||'',b.purchase_price].map(v=>`"${String(v).replaceAll('"','""')}"`).join(','))].join('\n');const blob=new Blob([csv],{type:'text/csv'});const url=URL.createObjectURL(blob);const a=document.createElement('a');a.href=url;a.download='pharma360-inventory.csv';a.click();URL.revokeObjectURL(url)};
  return <div className={`inventory-dashboard ${inventoryOnly?'inventory-standalone':''}`}>
    <div className="inventory-heading"><div><span className="inventory-eyebrow">STOCK CONTROL</span><h1>Inventory Management</h1><p>Track stock, manage batches, expiry and suppliers in real time.</p></div><div className="inventory-actions"><button className="inv-secondary" onClick={exportCsv}>↓ Export</button><button className="inv-secondary" disabled={importBusy} onClick={()=>document.getElementById('inventory-products-csv')?.click()}>↑ Import Products CSV</button><input id="inventory-products-csv" type="file" accept=".csv" hidden onChange={e=>{const f=e.target.files?.[0];if(f)importCsv('products',f);e.currentTarget.value='';}}/><button className="inv-secondary" disabled={importBusy} onClick={()=>document.getElementById('inventory-batches-csv')?.click()}>↑ Import Batches CSV</button><input id="inventory-batches-csv" type="file" accept=".csv" hidden onChange={e=>{const f=e.target.files?.[0];if(f)importCsv('batches',f);e.currentTarget.value='';}}/><button className="inv-primary" onClick={()=>setAddOpen(true)}>＋ Add Stock</button></div></div>
    {user.role==='super_admin'&&<div className="inv-import-store"><label>Import batches into store: <select value={importPharmacyId} onChange={e=>setImportPharmacyId(e.target.value)}><option value="">Select pharmacy/store</option>{stores.map((st:any)=><option value={st.id} key={st.id}>{st.name} · #{st.id}</option>)}</select></label></div>}
    <div className="inv-import-options"><label><input type="checkbox" checked={replaceCatalog} onChange={e=>setReplaceCatalog(e.target.checked)}/> Replace active product catalog (deactivate products not in CSV; preserve order history)</label><label><input type="checkbox" checked={replaceInventory} onChange={e=>setReplaceInventory(e.target.checked)}/> Replace stock batches for selected store (remove old batches before import)</label></div>
    {importMessage&&<div className="inv-import-message"><span>{importBusy?'⏳':'ℹ'}</span><div>{importMessage}</div><button onClick={()=>setImportMessage('')} aria-label="Dismiss import message">×</button></div>}
    <div className="inventory-hero"><div className="inventory-hero-copy"><span className="inventory-chip">✚ Pharma360 Inventory</span><h2>Keep essential<br/>medicines in stock</h2><p>Real-time stock, expiry alerts and smarter procurement for better patient care.</p><button className="inv-primary" onClick={()=>setAddOpen(true)}>＋ Add Stock</button> <button className="inv-secondary" onClick={()=>setTab('reports')}>View Reports</button></div><div className="inventory-hero-art"><div className="inv-pill-blister"><i/><i/><i/><i/><i/><i/></div><div className="inv-bottle"><span>✚<small>Pharma360</small></span></div><div className="inv-box">✚</div></div></div>
    <div className="inventory-stat-grid">
      <div className="inv-stat"><span className="stat-icon green">◇</span><label>Total Inventory Value</label><strong>₹{totalValue.toLocaleString('en-IN',{maximumFractionDigits:0})}</strong><small className="positive">● Live valuation</small><div className="mini-spark green-spark"/></div>
      <div className="inv-stat"><span className="stat-icon orange">▣</span><label>Items in Stock</label><strong>{totalUnits.toLocaleString('en-IN')}</strong><small>Across {rows.length} batches</small><div className="mini-spark orange-spark"/></div>
      <div className="inv-stat"><span className="stat-icon red">⚠</span><label>Low Stock Items</label><strong>{low.length}</strong><small className={low.length?'negative':'positive'}>{low.length?'Needs reorder review':'Stock levels healthy'}</small><div className="mini-spark red-spark"/></div>
      <div className="inv-stat"><span className="stat-icon purple">▣</span><label>Expiring (30 Days)</label><strong>{soon.length}</strong><small className={soon.length?'negative':'positive'}>{soon.length?'Expiry attention needed':'No urgent expiry'}</small><div className="mini-spark pink-spark"/></div>
      <div className="inv-stat"><span className="stat-icon teal">✓</span><label>Tracked Batches</label><strong>{rows.length}</strong><small>Batch visibility enabled</small><div className="mini-spark green-spark"/></div>
    </div>
    <div className="inventory-analytics-grid">
      <section className="inv-panel inv-trend"><div className="inv-panel-head"><h3>Inventory Trend</h3><select defaultValue="12"><option value="12">Last 12 Months</option><option value="6">Last 6 Months</option></select></div><div className="inv-chart"><ResponsiveContainer width="100%" height="100%"><AreaChart data={trendData}><CartesianGrid strokeDasharray="3 3" vertical={false}/><XAxis dataKey="month"/><YAxis/><Tooltip/><Area type="monotone" dataKey="restocked" stroke="#00a889" fill="#00a889" fillOpacity={0.12}/><Area type="monotone" dataKey="dispensed" stroke="#b65af2" fill="#b65af2" fillOpacity={0.12}/></AreaChart></ResponsiveContainer></div></section>
      <section className="inv-panel inv-category"><div className="inv-panel-head"><h3>Stock by Category</h3></div><div className="inv-category-body"><div className="inv-donut"><ResponsiveContainer width="100%" height="100%"><PieChart><Pie data={categoryData.length?categoryData:[{name:'No stock',value:1}]} dataKey="value" nameKey="name" innerRadius={55} outerRadius={78} paddingAngle={2}>{categoryData.map((_:any,i:number)=><Cell key={i} fill={['#3b91f5','#f6b51d','#0db99b','#ab67e9','#f36b9a','#ff8a48','#00a7c5'][i%7]}/>)}</Pie><Tooltip/></PieChart></ResponsiveContainer><div className="inv-donut-label"><b>{totalUnits.toLocaleString()}</b><small>Units</small></div></div><div className="inv-legend">{categoryData.slice(0,7).map((c:any,i:number)=><span key={c.name}><i style={{background:['#3b91f5','#f6b51d','#0db99b','#ab67e9','#f36b9a','#ff8a48','#00a7c5'][i%7]}}/>{c.name} <b>{c.value}</b></span>)}</div></div></section>
      <section className="inv-panel inv-alerts"><div className="inv-panel-head"><h3>Alerts & Notifications</h3><button className="inv-link" onClick={()=>setTab('low')}>View All</button></div>{low.slice(0,3).map((b:any,i:number)=><div className="inv-alert-row" key={b.id}><span className="alert-symbol">⚠</span><div><b>{b.product}</b><small>Only {b.quantity} units left</small></div><span className="alert-pill">Low Stock</span><small>{i+1}d</small></div>)}{soon.slice(0,2).map((b:any)=><div className="inv-alert-row" key={'exp'+b.id}><span className="alert-symbol amber">⌛</span><div><b>{b.product}</b><small>Expiring {b.expiry_date}</small></div><span className="alert-pill exp">Expiring</span></div>)}{!low.length&&!soon.length&&<div className="inv-empty-alert">No current inventory alerts.</div>}</section>
    </div>
    <div className="inventory-lower-grid"><section className="inv-panel inv-table-panel"><div className="inv-tabs"><button className={tab==='items'?'active':''} onClick={()=>setTab('items')}>Inventory Items</button><button className={tab==='batches'?'active':''} onClick={()=>setTab('batches')}>Batches</button><button className={tab==='expiring'?'active':''} onClick={()=>setTab('expiring')}>Expiring Soon <em>{soon.length}</em></button><button className={tab==='low'?'active':''} onClick={()=>setTab('low')}>Low Stock <em>{low.length}</em></button><button className={tab==='reports'?'active':''} onClick={()=>setTab('reports')}>Reports</button></div><div className="inv-filterbar"><input placeholder="⌕ Search drug, SKU, batch..." value={search} onChange={e => {
  setCategory(e.target.value);
  setInventoryPage(1);
}}/><select value={category} onChange={e=>{setCategory(e.target.value);setInventoryPage(1)}}><option value="all">All Categories</option>{categories.map((c:any)=><option key={c}>{c}</option>)}</select><select value={status} onChange={e=>{setStatus(e.target.value);setInventoryPage(1)}}><option value="all">All Status</option><option value="low">Low Stock</option><option value="in">In Stock</option><option value="expiring">Expiring</option></select></div><div className="inv-table-scroll"><table className="inv-table"><thead><tr><th>Product</th><th>SKU</th><th>Category</th><th>Stock</th><th>Batch No.</th><th>Expiry Date</th><th>Unit Price</th><th>Status</th></tr></thead><tbody>{pageRows.map((b:any)=><tr key={b.id}><td><b>{b.product}</b><small>Batch product</small></td><td>SKU-{String(b.product_id).padStart(3,'0')}</td><td><span className="inv-category-tag">{b.category}</span></td><td><b>{b.quantity}</b><span className="stock-bar"><i style={{width:`${Math.min(100,Math.max(5,b.quantity/10))}%`,background:b.quantity<=10?'#f43f5e':'#10b981'}}/></span></td><td>{b.batch_number}</td><td>{b.expiry_date||'—'}</td><td>₹{Number(b.purchase_price).toFixed(2)}</td><td><span className={`inv-status ${b.quantity<=10?'low':'ok'}`}>{b.quantity<=10?'Low Stock':'In Stock'}</span></td></tr>)}</tbody></table>{!tableRows.length&&<div className="empty-state">No matching inventory records.</div>}
{tableRows.length>0&&<div className="inv-pagination"><span>Showing {pageStart}–{pageEnd} of {tableRows.length} items · Sorted A–Z</span><div><button disabled={safePage<=1} onClick={()=>setInventoryPage(p=>Math.max(1,p-1))}>Prev</button>{getPaginationPages(safePage,totalPages).map((item,index)=>item==='…'?<span key={`ellipsis-${index}`} className="inv-pagination-ellipsis">…</span>:<button key={item} className={safePage===item?'active':''} onClick={()=>setInventoryPage(Number(item))}>{item}</button>)}<button disabled={safePage>=totalPages} onClick={()=>setInventoryPage(p=>Math.min(totalPages,p+1))}>Next</button></div></div>}</div></section><section className="inv-panel inv-suppliers"><div className="inv-panel-head"><h3>Supplier Management</h3><button className="inv-link">View All</button></div><div className="supplier-placeholder"><div className="supplier-icon">▦</div><div><b>Supplier information</b><small>Manage vendors from the Suppliers module.</small></div><span className="supplier-active">Connected</span></div><button className="supplier-cta" onClick={()=>window.location.href='/stores'}>＋ Manage Suppliers / Stores</button></section></div>
    {addOpen&&<div className="inv-modal-backdrop" onClick={()=>setAddOpen(false)}><div className="inv-modal" onClick={e=>e.stopPropagation()}><div className="inv-panel-head"><h3>Add Inventory Stock</h3><button onClick={()=>setAddOpen(false)}>×</button></div><form onSubmit={e=>{e.preventDefault();add.mutate()}}><label>Product<select required value={form.product_id} onChange={e=>setForm({...form,product_id:e.target.value})}><option value="">Select medicine</option>{products.map((p:any)=><option key={p.id} value={p.id}>{p.name} · {p.sku}</option>)}</select></label><label>Batch Number<input required value={form.batch_number} onChange={e=>setForm({...form,batch_number:e.target.value})}/></label><div className="inv-form-row"><label>Quantity<input required type="number" min="0" value={form.quantity} onChange={e=>setForm({...form,quantity:e.target.value})}/></label><label>Purchase price<input required type="number" min="0" step="0.01" value={form.purchase_price} onChange={e=>setForm({...form,purchase_price:e.target.value})}/></label></div><label>Expiry Date<input type="date" value={form.expiry_date} onChange={e=>setForm({...form,expiry_date:e.target.value})}/></label>{error&&<p className="inv-error">{error}</p>}{add.isError&&<p className="inv-error">Unable to add stock. Check the fields and your account permissions.</p>}<button className="inv-primary full" disabled={add.isPending}>{add.isPending?'Saving…':'Save Stock Batch'}</button></form></div></div>}
  </div>
}
export function Orders(){
  const qc=useQueryClient();
  const {data=[],isLoading,isError}=useQuery<any[]>({queryKey:['orders'],queryFn:async()=>(await api.get('/orders')).data,refetchInterval:10000});
  const {data:notifications=[]}=useQuery<any[]>({queryKey:['admin-order-notifications'],queryFn:async()=>(await api.get('/notifications')).data,refetchInterval:10000});
  const [search,setSearch]=useState('');
  const [filter,setFilter]=useState('all');
  const update=useMutation({
    mutationFn:async({id,status,reason}:{id:number;status:string;reason?:string})=>(await api.patch(`/orders/${id}/status`,null,{params:{status,reason}})).data,
    onSuccess:()=>{qc.invalidateQueries({queryKey:['orders']});qc.invalidateQueries({queryKey:['admin-order-notifications']});qc.invalidateQueries({queryKey:['summary']});}
  });
  const transitionOptions:Record<string,string[]>={pending:['accepted','rejected','cancelled'],accepted:['processing','cancelled'],processing:['packed','cancelled'],packed:['shipped','out_for_delivery','cancelled'],shipped:['out_for_delivery','delivered'],out_for_delivery:['delivered'],delivered:[],cancelled:[],rejected:[]};
  const statusLabel=(s:string)=>s.replace(/_/g,' ').replace(/\b\w/g,c=>c.toUpperCase());
  const pending=data.filter(o=>o.status==='pending').length;
  const active=data.filter(o=>['accepted','processing','packed','shipped','out_for_delivery'].includes(o.status)).length;
  const delivered=data.filter(o=>o.status==='delivered').length;
  const today=data.filter(o=>new Date(o.created_at).toDateString()===new Date().toDateString()).length;
  const filtered=data.filter(o=>{
    const text=(o.order_number+' '+o.customer_name+' '+o.customer_email+' '+o.customer_phone+' '+(o.pharmacy_name||'')).toLowerCase();
    return (!search||text.includes(search.toLowerCase()))&&(filter==='all'||o.status===filter);
  });
  const doAction=(o:any,status:string)=>{
    if(status==='rejected'||status==='cancelled'){
      const reason=window.prompt(`${status==='rejected'?'Reject':'Cancel'} order ${o.order_number}. Enter a reason:`);
      if(reason?.trim())update.mutate({id:o.id,status,reason});
    }else update.mutate({id:o.id,status});
  };
  const actions=(o:any)=>{
    const next=transitionOptions[o.status]||[];
    const labels:Record<string,string>={accepted:'Start processing',processing:'Mark packed',packed:'Out for delivery',shipped:'Out for delivery',out_for_delivery:'Mark delivered',delivered:'Completed'};
    const icons:Record<string,any>={accepted:Clock3,processing:PackageCheck,packed:Truck,shipped:Truck,out_for_delivery:CheckCircle2};
    const preferred=o.status==='packed'?(next.includes('out_for_delivery')?'out_for_delivery':'shipped'):o.status==='shipped'?'out_for_delivery':next.find(s=>!['rejected','cancelled'].includes(s));
    return <div className="order-actions-stack">
      {o.status==='pending'?<div className="order-decision-actions">
        <button className="order-accept-btn" disabled={update.isPending} onClick={()=>doAction(o,'accepted')}><CheckCircle2 size={13}/> Accept order</button>
        <button className="order-reject-btn" disabled={update.isPending} onClick={()=>doAction(o,'rejected')}><XCircle size={13}/> Reject</button>
      </div>:preferred&&<button className="order-primary-action" disabled={update.isPending} onClick={()=>doAction(o,preferred)}>{icons[preferred]&&React.createElement(icons[preferred],{size:14})}{labels[preferred]||statusLabel(preferred)}<ArrowRight size={13}/></button>}
      {next.includes('cancelled')&&o.status!=='pending'&&<button className="order-cancel-action" disabled={update.isPending} onClick={()=>doAction(o,'cancelled')}>Cancel order</button>}
      {o.status==='delivered'&&<span className="order-complete-label"><CheckCircle2 size={13}/> Fulfilled</span>}
      {['rejected','cancelled'].includes(o.status)&&<span className="order-complete-label muted"><XCircle size={13}/> Closed</span>}
    </div>;
  };
  return <>
    <div className="orders-hero">
      <div><div className="eyebrow">FULFILMENT CENTER</div><h1>Orders</h1><p>Review incoming orders, accept them and move every order through fulfilment to delivery.</p></div>
      <div className="orders-live"><span/><b>Live updates</b><small>Refreshes every 10 sec</small></div>
    </div>
    <div className="orders-kpi-grid">
      <div className="orders-kpi"><div className="orders-kpi-icon teal"><ClipboardList size={18}/></div><span>Total orders</span><b>{data.length}</b><small>All orders in your scope</small></div>
      <div className="orders-kpi"><div className="orders-kpi-icon amber"><Clock3 size={18}/></div><span>Awaiting acceptance</span><b>{pending}</b><small>Needs branch action</small></div>
      <div className="orders-kpi"><div className="orders-kpi-icon blue"><Truck size={18}/></div><span>In fulfilment</span><b>{active}</b><small>Accepted through delivery</small></div>
      <div className="orders-kpi"><div className="orders-kpi-icon green"><CheckCircle2 size={18}/></div><span>Delivered</span><b>{delivered}</b><small>Successfully fulfilled</small></div>
    </div>
    <div className="orders-secondary-stats">
      <div><span>Today</span><b>{today}</b></div><div><span>COD orders</span><b>{data.filter(o=>o.payment_method==='COD').length}</b></div><div><span>Paid orders</span><b>{data.filter(o=>o.payment_status==='paid').length}</b></div><div><span>Rejected / cancelled</span><b>{data.filter(o=>['rejected','cancelled'].includes(o.status)).length}</b></div>
    </div>
    <section className="panel orders-main-panel">
      <div className="orders-panel-heading"><div><div className="eyebrow">ORDER QUEUE</div><h2>Manage orders</h2><p>Accept new orders, then advance each order through its next fulfilment step.</p></div><button className="orders-refresh" onClick={()=>qc.invalidateQueries({queryKey:['orders']})}><RefreshCw size={14}/> Refresh</button></div>
      <div className="orders-controls"><label className="orders-search"><Search size={15}/><input value={search} onChange={e=>setSearch(e.target.value)} placeholder="Search order, customer, phone or branch"/></label><label className="orders-filter"><Filter size={14}/><select value={filter} onChange={e=>setFilter(e.target.value)}><option value="all">All statuses</option>{['pending','accepted','processing','packed','shipped','out_for_delivery','delivered','rejected','cancelled'].map(s=><option value={s} key={s}>{statusLabel(s)}</option>)}</select></label></div>
      <div className="orders-table-wrap"><table className="orders-table"><thead><tr><th>ORDER / ITEMS</th><th>CUSTOMER</th><th>BRANCH / FULFILMENT</th><th>DATE</th><th>AMOUNT</th><th>PAYMENT</th><th>STATUS & ACTIONS</th></tr></thead><tbody>{filtered.map(o=><tr key={o.id}>
        <td><b className="order-number">{o.order_number}</b><small className="order-items-summary">{(o.items||[]).map((it:any)=>`${it.name} × ${it.quantity}`).join(', ')}</small></td>
        <td><b>{o.customer_name||'Guest customer'}</b><small>{o.customer_email}</small><small>{o.customer_phone}</small></td>
        <td><b>{o.pharmacy_name||`Store #${o.pharmacy_id}`}</b><small className="fulfilment-pill">{o.fulfillment_type==='pickup'?'Store pickup':'Home delivery'}</small>{o.delivery_address&&<small className="order-address">{o.delivery_address}</small>}</td>
        <td>{new Date(o.created_at).toLocaleDateString('en-IN')}<small>{new Date(o.created_at).toLocaleTimeString('en-IN',{hour:'2-digit',minute:'2-digit'})}</small></td>
        <td className="table-money order-total">₹{Number(o.total||0).toLocaleString('en-IN',{minimumFractionDigits:2})}</td>
        <td><b className="payment-method">{o.payment_method}</b><small className={`payment-state ${o.payment_status}`}>{o.payment_status||'pending'}</small></td>
        <td><div className="order-status-action-cell"><span className={`status status-large ${o.status}`}>{statusLabel(o.status)}</span>{o.rejection_reason&&<small className="rejection-reason">Reason: {o.rejection_reason}</small>}{actions(o)}</div></td>
      </tr>)}</tbody></table>{isLoading&&<div className="empty-state">Loading orders…</div>}{isError&&<div className="error-box">Could not load orders. Check backend connection.</div>}{!isLoading&&!filtered.length&&<div className="empty-state">{data.length?'No orders match your search or filter.':'No orders yet. Customer checkout orders will appear here after placement.'}</div>}</div>
    </section>
    <section className="panel table-panel admin-notifications-panel orders-notifications">
      <div className="table-toolbar"><div><h3>Order notifications</h3><p>In-app order alerts for your branch and admin account.</p></div><span className="soft-tag"><Bell size={14}/> {notifications.length} alerts</span></div>
      <div className="admin-notification-list">{notifications.slice(0,20).map(n=><article key={n.id} className="admin-notification"><div className="notification-icon"><Bell size={15}/></div><div><b>{n.title}</b><p>{n.message}</p><small>{n.channel.toUpperCase()} · {n.delivery_status} · {new Date(n.created_at).toLocaleString('en-IN')}</small></div></article>)}{!notifications.length&&<div className="empty-state">No order notifications yet.</div>}</div>
    </section>
  </>;
}
export function Financials(){const {data}=useQuery<any>({queryKey:['summary'],queryFn:async()=>(await api.get('/dashboard/summary')).data});return <><div className="page-heading"><div><div className="eyebrow">FINANCE & ACCOUNTING</div><h1>Financial overview</h1><p>Management view of recorded delivered sales, COGS and expenses.</p></div></div><div className="kpi-grid"><div className="kpi-card"><span>Total revenue</span><strong>₹{(data?.revenue||0).toLocaleString('en-IN')}</strong><small>Delivered orders only</small></div><div className="kpi-card"><span>Cost of goods sold</span><strong>₹{((data?.revenue||0)-(data?.gross_profit||0)).toLocaleString('en-IN')}</strong><small>Batch purchase cost</small></div><div className="kpi-card"><span>Operating expenses</span><strong>₹{(data?.expenses||0).toLocaleString('en-IN')}</strong><small>Recorded expenses</small></div><div className="kpi-card"><span>Net profit</span><strong className="positive">₹{(data?.net_profit||0).toLocaleString('en-IN')}</strong><small>Gross profit less expenses</small></div></div><section className="panel finance-note"><Wallet size={22}/><div><h3>Accounting integrity</h3><p>Profit figures are calculated from delivered order line-item costs and recorded expenses. For statutory accounting, add tax ledgers, returns, discounts, supplier invoices, payment settlements and reconciliation before production use.</p></div></section></>}
export function GenericPage({title,desc,icon:Icon=ClipboardList}:{title:string;desc:string;icon?:any}){return <><div className="page-heading"><div><div className="eyebrow">OPERATIONS</div><h1>{title}</h1><p>{desc}</p></div></div><section className="panel empty-feature"><div className="empty-feature-icon"><Icon size={28}/></div><h3>{title} workspace</h3><p>This module is scaffolded in the PHARMA360 project architecture. Connect the relevant provider and complete the workflow before enabling it for live operations.</p></section></>}
