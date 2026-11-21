import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { Boxes, HeartPulse, ShieldCheck } from 'lucide-react';
import { api, saveSession } from '../lib/api';

export default function InventoryLogin() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  const nav = useNavigate();

  async function submit(e: React.FormEvent) {
    e.preventDefault();

    setBusy(true);
    setError('');

    try {
      const { data } = await api.post('/auth/login', {
        email,
        password,
      });

      if (
        !['inventory_manager', 'super_admin'].includes(
          data.user.role
        )
      ) {
        setError(
          'This login is for Inventory staff. Please use the main admin login.'
        );
        return;
      }

      saveSession(data.access_token, data.user);

      nav(
        data.user.role === 'super_admin'
          ? '/inventory'
          : '/inventory/workspace'
      );
    } catch (err: any) {
      setError(
        err.response?.data?.detail ||
          'Unable to sign in. Check your credentials.'
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="inventory-login">
      <div className="inventory-login-card">
        <div className="inv-login-brand">
          <div>
            <HeartPulse />
          </div>

          <b>
            PHARMA<span>360</span>
          </b>
        </div>

        <div className="inv-login-icon">
          <Boxes />
        </div>

        <span className="inventory-eyebrow">
          STOCK CONTROL ACCESS
        </span>

        <h1>Inventory Staff Login</h1>

        <p>
          Sign in to manage batches, stock levels and expiry alerts.
        </p>

        <form onSubmit={submit}>
          <label>
            Email address
            <input
              type="email"
              autoComplete="username"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="inventory@pharmacy.com"
            />
          </label>

          <label>
            Password
            <input
              type="password"
              autoComplete="current-password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Enter password"
            />
          </label>

          {error && (
            <div className="inv-login-error">
              {error}
            </div>
          )}

          <button
            className="inv-primary full"
            disabled={busy}
          >
            {busy
              ? 'Signing in…'
              : 'Sign in to Inventory'}
          </button>
        </form>

        <div className="inv-login-security">
          <ShieldCheck size={16} />
          Role-protected inventory workspace
        </div>

        <Link to="/login">
          ← Main admin login
        </Link>
      </div>
    </div>
  );
}