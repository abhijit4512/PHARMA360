import { NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom';
import {
  Activity, Boxes, Building2, HeartPulse, LayoutDashboard, LogOut,
  Package, ShoppingBag, Truck, Users, Wallet, Menu, X, Bell, Search,
} from 'lucide-react';
import { useState } from 'react';
import { clearSession, getUser } from '../lib/api';

const links = [
  ['Overview', '/dashboard', LayoutDashboard],
  ['Pharmacy Stores', '/stores', Building2],
  ['Products', '/products', Package],
  ['Inventory', '/inventory', Boxes],
  ['Orders', '/orders', ShoppingBag],
  ['Financials', '/financials', Wallet],
  ['Customers', '/customers', Users],
  ['Delivery', '/delivery', Truck],
] as const;

export default function Layout() {
  const nav = useNavigate();
  const location = useLocation();
  const user = getUser();
  const [mobileOpen, setMobileOpen] = useState(false);
  const [profileOpen, setProfileOpen] = useState(false);
  const current = links.find(([, path]) => path === location.pathname)?.[0] || 'Overview';
  const logout = () => { clearSession(); nav('/login'); };

  return (
    <div className="app-shell">
      {mobileOpen && <button className="sidebar-scrim" aria-label="Close navigation" onClick={() => setMobileOpen(false)} />}
      <aside className={`sidebar ${mobileOpen ? 'sidebar-open' : ''}`}>
        <div className="brand">
          <div className="brand-mark"><HeartPulse size={22} /></div>
          <div><b>PHARMA<span>360</span></b><small>BUSINESS OS</small></div>
          <button className="mobile-close" onClick={() => setMobileOpen(false)} aria-label="Close menu"><X size={19}/></button>
        </div>
        <div className="workspace-label">WORKSPACE</div>
        <nav>
          {links.filter(([label]) => user?.role==='inventory_manager' ? label==='Inventory' : (user?.role==='super_admin' || label!=='Pharmacy Stores')).map(([label, path, Icon]) => (
            <NavLink key={path} to={path} onClick={() => setMobileOpen(false)} className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}>
              <Icon size={18}/><span>{label}</span>{label === 'Orders' && <i className="nav-dot"/>}
            </NavLink>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <div className="support-card">
            <div className="support-icon"><Activity size={17}/></div>
            <b>Business health</b>
            <p>Your workspace is ready. Monitor stores, inventory and operations from one place.</p>
            <span className="support-status"><i/> All systems operational</span>
          </div>
          <button className="nav-link logout" onClick={logout}><LogOut size={18}/><span>Sign out</span></button>
        </div>
      </aside>

      <main className="main-area">
        <header className="topbar">
          <div className="topbar-left">
            <button className="menu-toggle" onClick={() => setMobileOpen(true)} aria-label="Open navigation"><Menu size={20}/></button>
            <div className="crumb"><span>Workspace</span><b>{current}</b></div>
          </div>
          <div className="top-actions">
            <div className="global-search"><Search size={15}/><span>Search workspace</span><kbd>⌘ K</kbd></div>
            <button className="top-icon-btn" aria-label="Notifications"><Bell size={18}/><i/></button>
            <span className="live-pill"><i/> System online</span>
            <div className="profile-menu-wrap">
              <button className="profile-trigger" onClick={() => setProfileOpen(v => !v)} aria-expanded={profileOpen} aria-label="Open account menu">
                <div className="avatar">{user?.name?.slice(0, 1) || 'A'}</div>
                <div className="user-meta"><b>{user?.name || 'Administrator'}</b><small>{user?.role?.replace('_', ' ') || 'Admin'}</small></div>
              </button>
              {profileOpen && <div className="profile-dropdown">
                <div className="profile-dropdown-head"><b>{user?.name || 'Administrator'}</b><small>{user?.role?.replace('_', ' ') || 'Admin'}</small></div>
                <button className="profile-logout" onClick={() => { setProfileOpen(false); logout(); }}><LogOut size={16}/> Logout</button>
              </div>}
            </div>
          </div>
        </header>
        <div className="page-wrap"><Outlet/></div>
      </main>
    </div>
  );
}
