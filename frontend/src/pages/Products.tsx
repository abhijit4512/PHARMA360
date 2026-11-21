import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { api } from '../lib/api';
import { Plus, Search, Package, ShieldCheck } from 'lucide-react';

type Product = {
  id: number;
  sku: string;
  name: string;
  generic_name: string;
  brand: string;
  category: string;
  mrp: number;
  selling_price: number;
  prescription_required: boolean;
  stock: number;
};

const PAGE_SIZE = 10;

function getPaginationPages(currentPage: number, totalPages: number): (number | '…')[] {
  if (totalPages <= 7) return Array.from({ length: totalPages }, (_, i) => i + 1);
  if (currentPage <= 2) return [1, 2, 3, '…', totalPages - 1, totalPages];
  if (currentPage >= totalPages - 1) return [1, 2, '…', totalPages - 2, totalPages - 1, totalPages];
  return [1, '…', currentPage - 1, currentPage, currentPage + 1, '…', totalPages];
}

export default function Products() {
  const qc = useQueryClient();
  const { data = [] } = useQuery<Product[]>({
    queryKey: ['products'],
    queryFn: async () => (await api.get('/products')).data,
  });
  const [search, setSearch] = useState('');
  const [page, setPage] = useState(1);
  const [show, setShow] = useState(false);
  const [f, setF] = useState({
    sku: '', name: '', generic_name: '', brand: '', category: 'OTC Medicines',
    description: '', mrp: 0, selling_price: 0, prescription_required: false, image_url: '',
  });

  const create = useMutation({
    mutationFn: () => api.post('/products', f),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['products'] });
      setShow(false);
    },
  });

  const filteredRows = data.filter(p =>
    (p.name + p.brand + p.sku + p.category).toLowerCase().includes(search.toLowerCase()),
  );
  const rows = [...filteredRows].sort((a, b) =>
    String(a.name || '').localeCompare(String(b.name || ''), undefined, { sensitivity: 'base' }),
  );
  const totalPages = Math.max(1, Math.ceil(rows.length / PAGE_SIZE));
  const safePage = Math.min(page, totalPages);
  const pageStart = rows.length ? (safePage - 1) * PAGE_SIZE + 1 : 0;
  const pageEnd = Math.min(safePage * PAGE_SIZE, rows.length);
  const pageRows = rows.slice((safePage - 1) * PAGE_SIZE, safePage * PAGE_SIZE);

  return <>
    <div className="page-heading">
      <div><div className="eyebrow">CATALOG MANAGEMENT</div><h1>Product catalog</h1><p>One central catalog connected to each pharmacy's local inventory.</p></div>
      <button className="primary-btn" onClick={() => setShow(true)}><Plus size={17}/> Add product</button>
    </div>
    <div className="mini-stat-row">
      <div className="mini-stat"><span>Active products</span><b>{data.length}</b></div>
      <div className="mini-stat"><span>Prescription required</span><b>{data.filter(p => p.prescription_required).length}</b></div>
      <div className="mini-stat"><span>Categories</span><b>{new Set(data.map(p => p.category)).size}</b></div>
    </div>
    <section className="panel table-panel">
      <div className="table-toolbar">
        <div><h3>All products</h3><p>Product pricing and availability overview.</p></div>
        <div className="search-box"><Search size={16}/><input placeholder="Search products…" value={search} onChange={e => { setSearch(e.target.value); setPage(1); }}/></div>
      </div>
      <div className="table-scroll">
        <table>
          <thead><tr><th>PRODUCT</th><th>CATEGORY</th><th>MRP</th><th>SELLING PRICE</th><th>NETWORK STOCK</th><th>TYPE</th></tr></thead>
          <tbody>{pageRows.map(p => <tr key={p.id}>
            <td><div className="product-cell"><div className="product-thumb"><Package size={18}/></div><div><b>{p.name}</b><small>{p.sku} · {p.brand}</small></div></div></td>
            <td>{p.category}</td><td className="muted-cell">₹{Number(p.mrp || 0).toFixed(2)}</td><td className="table-money">₹{Number(p.selling_price || 0).toFixed(2)}</td><td>{p.stock}</td>
            <td>{p.prescription_required ? <span className="soft-tag"><ShieldCheck size={13}/> Rx required</span> : <span className="soft-tag">OTC / General</span>}</td>
          </tr>)}</tbody>
        </table>
        {rows.length === 0 && <div className="empty-state">No products found.</div>}
        {rows.length > 0 && <div className="inv-pagination">
          <span>Showing {pageStart}–{pageEnd} of {rows.length} products · Sorted A–Z</span>
          <div>
            <button disabled={safePage <= 1} onClick={() => setPage(p => Math.max(1, p - 1))}>Prev</button>
            {getPaginationPages(safePage, totalPages).map((item, index) => item === '…' ?
              <span className="pagination-ellipsis" key={`ellipsis-${index}`}>…</span> :
              <button key={item} className={safePage === item ? 'active' : ''} onClick={() => setPage(item)}>{item}</button>
            )}
            <button disabled={safePage >= totalPages} onClick={() => setPage(p => Math.min(totalPages, p + 1))}>Next</button>
          </div>
        </div>}
      </div>
    </section>
    {show && <div className="modal-backdrop"><form className="modal" onSubmit={e => { e.preventDefault(); create.mutate(); }}>
      <div className="modal-head"><div><h2>Add catalog product</h2><p>New product will be available to stores after inventory is added.</p></div><button type="button" className="icon-btn" onClick={() => setShow(false)}>×</button></div>
      <div className="form-grid">{([['sku','SKU'],['name','Product name'],['generic_name','Generic name'],['brand','Brand'],['category','Category'],['mrp','MRP'],['selling_price','Selling price'],['description','Description']] as const).map(([k,l]) => <label key={k}>{l}<input required={['sku','name','category'].includes(k)} type={['mrp','selling_price'].includes(k) ? 'number' : 'text'} step="0.01" value={(f as any)[k]} onChange={e => setF({ ...f, [k]: ['mrp','selling_price'].includes(k) ? Number(e.target.value) : e.target.value })}/></label>)}
        <label className="check-label"><input type="checkbox" checked={f.prescription_required} onChange={e => setF({ ...f, prescription_required: e.target.checked })}/> Prescription required</label>
      </div>
      {create.isError && <div className="error-box">{(create.error as any)?.response?.data?.detail || 'Unable to add product'}</div>}
      <div className="modal-actions"><button type="button" className="outline-btn" onClick={() => setShow(false)}>Cancel</button><button className="primary-btn" disabled={create.isPending}>{create.isPending ? 'Saving…' : 'Save product'}</button></div>
    </form></div>}
  </>;
}
