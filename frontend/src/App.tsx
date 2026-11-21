import {Navigate,Outlet,Route,Routes} from 'react-router-dom';
import Layout from './components/Layout';
import Login from './pages/Login';
import InventoryLogin from './pages/InventoryLogin';
import Dashboard from './pages/Dashboard';
import Stores from './pages/Stores';
import Products from './pages/Products';
import {Financials,GenericPage,Inventory,Orders} from './pages/Operations';
import Shop from './pages/Shop';
import CustomerAuth from './pages/CustomerAuth';
import CustomerNotifications from './pages/CustomerNotifications';
import {getUser,clearSession} from './lib/api';
import {LogOut} from 'lucide-react';
import {Truck,Users} from 'lucide-react';
import Customers from './pages/Customers';
import Delivery from './pages/Delivery';
function Protected(){const user=getUser();return user&&user.role!=='customer'&&user.role!=='inventory_manager'?<Outlet/>:<Navigate to={user? (user.role==='inventory_manager'?'/inventory/workspace':'/shop'):'/login'} replace/>}
function InventoryProtected() {
  const user = getUser();

  return user?.role === 'inventory_manager' ? (
    <div className="inventory-workspace-shell">
      <header>
        <div className="inv-workspace-brand">
          ✚ <b>PHARMA<span>360</span></b>
          <small>Inventory Workspace</small>
        </div>

        <div className="inv-workspace-user">
          <span>{user.name}</span>
          <button
            onClick={() => {
              clearSession();
              window.location.href = '/inventory/login';
            }}
          >
            <LogOut size={16} /> Sign out
          </button>
        </div>
      </header>

      <main>
        <Inventory />
      </main>
    </div>
  ) : (
    <Navigate
      to={user ? '/dashboard' : '/inventory/login'}
      replace
    />
  );
}
function ProtectedCustomer(){return getUser()?.role==='customer'?<Outlet/>:<Navigate to="/customer/login" replace/>}
export default function App(){return <Routes>
<Route path="/" element={<Navigate to="/shop" replace/>}/>
<Route path="/shop" element={<Shop/>}/>
<Route path="/customer/login" element={<CustomerAuth/>}/>
<Route path="/customer/register" element={<CustomerAuth/>}/>
<Route element={<ProtectedCustomer/>}><Route path="/customer/notifications" element={<CustomerNotifications/>}/></Route>
<Route path="/login" element={<Login/>}/><Route path="/inventory/login" element={<InventoryLogin/>}/>
<Route path="/inventory/workspace" element={<InventoryProtected/>}/>
<Route element={<Protected/>}><Route element={<Layout/>}>
<Route path="/dashboard" element={<Dashboard/>}/><Route path="/stores" element={<Stores/>}/><Route path="/products" element={<Products/>}/><Route path="/inventory" element={<Inventory/>}/><Route path="/orders" element={<Orders/>}/><Route path="/financials" element={<Financials/>}/>
<Route path="/customers" element={<Customers/>}/>
<Route path="/delivery" element={<Delivery/>}/>
</Route></Route>
<Route path="*" element={<Navigate to="/shop" replace/>}/></Routes>}
