import React, {useState} from 'react';
import {useQuery, useMutation, useQueryClient} from '@tanstack/react-query';import {api} from '../lib/api';import {Boxes,ClipboardList,Wallet,Truck,Users,AlertTriangle,Bell,CheckCircle2,XCircle,Clock3,PackageCheck,Search,Filter,ArrowRight,RefreshCw} from 'lucide-react';
export function Inventory(){const {data=[]}=useQuery<any[]>({queryKey:['inventory'],queryFn:async()=>(await api.get('/inventory')).data});return <><div className="page-heading"><div><div className="eyebrow">STOCK CONTROL</div><h1>Inventory & batches</h1><p>Track batch-level quantities, purchase costs and expiry dates.</p></div></div><div className="mini-stat-row"><div className="mini-stat"><span>Tracked batches</span><b>{data.length}</b></div><div className="mini-stat"><span>Units on hand</span><b>{data.reduce((a,b)=>a+b.quantity,0)}</b></div><div className="mini-stat"><span>Low quantity batches</span><b>{data.filter(b=>b.quantity<=10).length}</b></div></div><section className="panel table-panel"><div className="table-toolbar"><div><h3>Batch inventory</h3><p>FEFO-ready batch visibility across your authorized stores.</p></div><span className="soft-tag"><Boxes size={14}/> Batch-level stock</span></div><div className="table-scroll"><table><thead><tr><th>PRODUCT</th><th>STORE</th><th>BATCH</th><th>QUANTITY</th><th>PURCHASE COST</th><th>EXPIRY</th></tr></thead><tbody>{data.map(b=><tr key={b.id}><td><b>{b.product}</b></td><td>Store #{b.pharmacy_id}</td><td>{b.batch_number}</td><td><span className={b.quantity<=10?'warning-number':''}>{b.quantity}</span></td><td>₹{b.purchase_price.toFixed(2)}</td><td>{b.expiry_date||'Not recorded'}</td></tr>)}</tbody></table>{!data.length&&<div className="empty-state">No inventory batches yet. Add batches through the inventory API or seeded demo data.</div>}</div></section></>}
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
