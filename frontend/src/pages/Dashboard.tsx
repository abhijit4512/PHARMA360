import { useQuery } from '@tanstack/react-query';
import { api, getUser } from '../lib/api';
import {
  Activity, ArrowUpRight, Boxes, Building2, CalendarDays, IndianRupee,
  Package, RefreshCw, ShoppingCart, TrendingUp, TriangleAlert, Truck,
} from 'lucide-react';
import {
  Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts';

const money = (n: number) => new Intl.NumberFormat('en-IN', {
  style: 'currency', currency: 'INR', maximumFractionDigits: 0,
}).format(n || 0);

export default function Dashboard() {
  const user = getUser();
  const { data, isLoading, error, refetch, isFetching } = useQuery({
    queryKey: ['summary'], queryFn: async () => (await api.get('/dashboard/summary')).data,
  });
  const cards = [
    { label: 'Total revenue', value: money(data?.revenue), sub: 'From delivered orders', icon: IndianRupee, tone: 'teal' },
    { label: 'Net profit', value: money(data?.net_profit), sub: 'After recorded expenses', icon: TrendingUp, tone: 'green' },
    { label: 'Total orders', value: (data?.orders || 0).toLocaleString('en-IN'), sub: `${data?.orders_today || 0} placed today`, icon: ShoppingCart, tone: 'blue' },
    { label: user?.role === 'super_admin' ? 'Active stores' : 'Stock units', value: user?.role === 'super_admin' ? (data?.active_stores || 0).toLocaleString('en-IN') : (data?.stock_units || 0).toLocaleString('en-IN'), sub: user?.role === 'super_admin' ? `${data?.store_count || 0} registered locations` : 'Across your pharmacy', icon: Building2, tone: 'violet' },
  ];

  return <div className="dashboard-page">
    <div className="page-heading dashboard-heading">
      <div>
        <div className="eyebrow"><span className="eyebrow-dot"/> BUSINESS OVERVIEW</div>
        <h1>Good to see you, {user?.name?.split(' ')[0] || 'Admin'}.</h1>
        <p>Here’s your pharmacy network at a glance. Here’s what needs your attention today.</p>
      </div>
      <div className="heading-actions">
        <span className="date-chip"><CalendarDays size={14}/>{new Date().toLocaleDateString('en-IN', { weekday: 'short', day: '2-digit', month: 'short', year: 'numeric' })}</span>
        <button className="outline-btn refresh-btn" onClick={() => refetch()} disabled={isFetching}><RefreshCw size={14} className={isFetching ? 'spin' : ''}/> Refresh data</button>
      </div>
    </div>

    {error && <div className="error-box">Unable to load live metrics. Check the backend connection and your login session.</div>}

    {isLoading ? <div className="loading-card">Loading your business overview…</div> : <>
      <div className="section-kicker"><span>PERFORMANCE SNAPSHOT</span><small>Live figures from your connected database</small></div>
      <div className="kpi-grid">
        {cards.map((card) => <article className="kpi-card" key={card.label}>
          <div className="kpi-top"><span>{card.label}</span><div className={`kpi-icon ${card.tone}`}><card.icon size={19}/></div></div>
          <strong>{card.value}</strong>
          <div className="kpi-foot"><span>{card.sub}</span><span className="kpi-live"><i/> Live</span></div>
        </article>)}
      </div>

      <div className="dashboard-grid">
        <section className="panel revenue-panel">
          <div className="panel-head"><div><span className="panel-overline">REVENUE TRENDS</span><h3>Revenue performance</h3><p>Delivered order revenue · last 6 months</p></div><span className="legend"><i/> Revenue</span></div>
          <div className="chart-area"><ResponsiveContainer width="100%" height="100%"><AreaChart data={data?.monthly_sales || []} margin={{ top: 12, right: 8, left: 0, bottom: 0 }}>
            <defs><linearGradient id="revFill" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#0e9f83" stopOpacity={0.24}/><stop offset="95%" stopColor="#0e9f83" stopOpacity={0.01}/></linearGradient></defs>
            <CartesianGrid stroke="#edf2f1" vertical={false}/>
            <XAxis dataKey="month" axisLine={false} tickLine={false} tick={{ fill: '#8a9998', fontSize: 11 }}/>
            <YAxis axisLine={false} tickLine={false} tick={{ fill: '#8a9998', fontSize: 10 }} tickFormatter={v => `₹${v / 1000}k`} width={48}/>
            <Tooltip formatter={(v: any) => money(Number(v))} contentStyle={{ border: '1px solid #e8efed', borderRadius: 12, boxShadow: '0 12px 35px #173c3514', fontSize: 12 }}/>
            <Area type="monotone" dataKey="revenue" stroke="#0e9f83" strokeWidth={3} fill="url(#revFill)" activeDot={{ r: 5, strokeWidth: 0, fill: '#087e69' }}/>
          </AreaChart></ResponsiveContainer></div>
        </section>

        <section className="panel health-panel">
          <div className="panel-head"><div><span className="panel-overline">DAILY OPERATIONS</span><h3>Operations snapshot</h3><p>Orders and inventory requiring attention</p></div><span className="soft-tag"><Activity size={12}/> Live data</span></div>
          <div className="snapshot-list">
            <div><span className="snapshot-icon amber"><ShoppingCart size={17}/></span><div><b>Pending orders</b><small>Awaiting store action</small></div><strong>{data?.pending_orders || 0}</strong></div>
            <div><span className="snapshot-icon green"><Package size={17}/></span><div><b>Delivered orders</b><small>Successfully completed</small></div><strong>{data?.delivered_orders || 0}</strong></div>
            <div><span className="snapshot-icon blue"><Boxes size={17}/></span><div><b>Low stock items</b><small>10 units or fewer per batch</small></div><strong>{data?.low_stock || 0}</strong></div>
            <div><span className="snapshot-icon red"><TriangleAlert size={17}/></span><div><b>Near expiry batches</b><small>Expiry within 90 days</small></div><strong>{data?.expiring_batches || 0}</strong></div>
          </div>
        </section>
      </div>

      <div className="bottom-grid">
        <section className="panel payment-panel"><div className="panel-head"><div><span className="panel-overline">PAYMENT & STOCK</span><h3>Business at a glance</h3><p>Payment collection and inventory position</p></div></div>
          <div className="payment-stats">
            <div><span>COD orders</span><b>{data?.cod_orders || 0}</b><small>Cash on delivery</small></div>
            <div><span>Paid orders</span><b>{data?.paid_orders || 0}</b><small>Payment confirmed</small></div>
            <div><span>Inventory value</span><b>{money(data?.inventory_value || 0)}</b><small>Current stock valuation</small></div>
          </div>
        </section>
        <section className="insight-card"><div className="insight-symbol"><Activity size={21}/></div><div><span className="panel-overline">SMART OPERATIONS</span><b>Business intelligence</b><p>Connect Google ADK and Gemini credentials to enable natural-language business insights and stock recommendations.</p></div><span className="coming-tag">Setup required</span></section>
      </div>
      <div className="dashboard-footnote"><span><Truck size={14}/> PHARMA360 Business OS</span><span>Metrics reflect records currently available in your database.</span></div>
    </>}
  </div>;
}
