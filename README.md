# PHARMA360 — Multi-store pharmacy business platform

PHARMA360 is a new full-stack starter implementation for a pharmacy network: separate Super Admin and store-owner authentication, store-scoped API access, product catalog, batch inventory, order lifecycle, financial summary, and a customer-facing catalog shell.

> **Important delivery status:** This is a runnable foundation / MVP, not yet a legally or operationally production-ready pharmacy system. The project includes working authentication, store provisioning, catalog creation, batch inventory reads, order creation/status updates, and summary calculations. Several master-prompt modules are intentionally scaffolds or integration points: full customer registration/checkout and address book, Razorpay live payments/webhooks, COD reconciliation, delivery-partner workflows/live GPS, prescription file storage and pharmacist review, supplier procurement, employee/attendance, returns/refunds, GST-compliant accounting, WhatsApp/SMS/email providers, Google Maps, and Google ADK agents. Do not process real medicine orders or payments until those modules, security review, licensing and applicable Indian legal/compliance checks are completed.

## Architecture

- `frontend/`: React + TypeScript + Vite + Tailwind + React Query + Recharts
- `backend/`: FastAPI + SQLAlchemy 2 + Pydantic + JWT
- `database`: PostgreSQL (SQLite is used as a local fallback if `DATABASE_URL` is omitted)
- `docker-compose.yml`: PostgreSQL + API containers

## Quick start — Windows PowerShell (without Docker)

### 1. PostgreSQL

Install PostgreSQL 16+ and create a database named `pharma360`.

### 2. Backend

```powershell
cd pharma360\backend
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
```

Edit `.env` and set a strong `JWT_SECRET`, database credentials, and a new `SUPERADMIN_PASSWORD`. Then initialize demo data:

```powershell
python seed.py
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

API health: http://127.0.0.1:8000/health  
Swagger API docs: http://127.0.0.1:8000/docs

### 3. Frontend (new terminal)

```powershell
cd pharma360\frontend
npm install
Copy-Item .env.example .env
npm run dev
```

Open http://localhost:5173

## Demo accounts

Seed script creates the following demo credentials only when the corresponding users/stores do not already exist:

| Role | Email | Password |
|---|---|---|
| Super Admin | `admin@pharma360.local` | `ChangeMe123!` (or your `.env` value on first seed) |
| Store owner | `banjara@pharma360.local` | `StoreDemo123!` |
| Store owner | `madhapur@pharma360.local` | `StoreDemo123!` |
| Store owner | `kukatpally@pharma360.local` | `StoreDemo123!` |

**Change all demo passwords and the JWT secret before deployment.** The store owner login uses the store email. Public self-registration is not implemented.

## Main routes

- `/shop` — customer-facing product catalog
- `/login` — staff/admin login
- `/dashboard` — KPI overview
- `/stores` — Super Admin store management
- `/products` — product catalog management
- `/inventory` — batch inventory overview
- `/orders` — order monitoring
- `/financials` — revenue, COGS and recorded expense summary

## API overview

- `POST /api/auth/login`, `GET /api/auth/me`
- `GET /api/dashboard/summary`
- `GET/POST /api/stores`, `PATCH /api/stores/{id}/status` (Super Admin)
- `GET/POST /api/products`
- `GET /api/inventory`, `POST /api/inventory/batches`
- `GET/POST /api/orders`, `PATCH /api/orders/{id}/status`
- `POST /api/expenses`

All authenticated store users are filtered to their own `pharmacy_id` for store-scoped records. Super Admin can view network-wide records. For production, strengthen this further with PostgreSQL row-level security, comprehensive permission scopes, audit coverage, rate limiting, refresh-token rotation, MFA and security testing.

## Current business calculation notes

- Revenue in the summary is the sum of delivered order totals.
- COGS is calculated from order-line batch purchase cost captured when the order is placed.
- Gross profit = delivered revenue − recorded COGS.
- Net profit = gross profit − recorded expenses.
- Inventory valuation = remaining batch quantity × recorded purchase cost.
- Low-stock alert is currently a simple batch quantity threshold (10); configurable per-SKU/store reorder levels are not yet implemented.

These management estimates are not a substitute for a complete accounting ledger. Add tax, discounts, refunds, purchase invoices, payment settlement and reconciliation ledgers before relying on statutory or audited reports.

## Environment integrations to add

Never commit real credentials. Add server-side secrets for Razorpay key/secret and webhook secret, Google Maps API key, WhatsApp Cloud API token/phone-number ID, email/SMS provider credentials, Gemini API key and Google ADK configuration. Implement and test provider webhooks before enabling real payments or notifications.

## Suggested next implementation milestones

1. Alembic-managed migrations and PostgreSQL row-level security.
2. Customer accounts, addresses, cart persistence, serviceability and checkout.
3. Prescription upload, pharmacist verification and dispensing audit trail.
4. Razorpay order creation, signature verification, idempotent webhooks, refunds and COD reconciliation.
5. Suppliers, purchase orders, goods receipt, supplier balances and FEFO reservation/release.
6. Delivery-partner app, assignment, status timeline, location consent and proof of delivery.
7. Full accounting ledger, GST invoice rules, returns and credit notes.
8. Google ADK agent tools with read-only analytics by default and human approval for mutations.
9. Automated API, integration and end-to-end tests; backups, monitoring and deployment hardening.

## Safety and compliance

Only appropriately licensed pharmacies and qualified pharmacists should dispense regulated medicines. Prescription-only products must not be sold until a valid prescription and pharmacist approval workflow is implemented. The seeded products and sample data are demonstration data. Validate applicable Indian drug-sale, pharmacy, GST, consumer-protection and DPDP requirements with qualified professionals before launch.


## Customer login, catalog and notification preferences (added)
- Customer account registration and login: `/customer/login` (toggle Create account).
- Public product browsing uses `/api/catalog/products` and category list `/api/catalog/categories`; no customer token is needed.
- Seed catalog now includes 20 categories with 10 products each (200 catalog entries). Products are sample catalog records; verify legal product details, prices, brands, images and prescription flags before production.
- Customer notification preferences API: `GET/PUT /api/notifications/preferences` (requires customer bearer token). Preferences are stored for email, SMS, WhatsApp, order updates and offers. Delivery integrations require provider credentials and workers to be configured separately.
- Re-run `python seed.py` only if you understand it is additive and the seed products are only created when the products table is empty. Existing database product rows are not replaced.

## Customer navbar and demo stock update

The storefront now reads the persisted customer session and displays the customer's name, notification shortcut, and logout button. It uses the unauthenticated public catalog endpoint (`/api/catalog/products`) so customers can browse without an admin/store token. Demo inventory batches are seeded independently of catalog creation, and only missing demo batches are added; existing inventory is preserved.

To add demo stock to an existing database, run from the backend directory:

```powershell
python seed.py
```

This seed operation is idempotent for its demo batches and does not reset the database.


## Customer checkout, branch routing and order notifications

- Customers sign in, add products to a cart, select delivery or pickup, enter a contact phone, and choose a branch that has stock for the entire cart.
- Branches are prioritized by city/area match. Customers may use browser location to rank branches by distance when the branch has latitude/longitude configured. Store coordinates can be entered when creating a pharmacy in Admin → Pharmacy Stores. Existing branches with no coordinates can still be selected by city/area.
- Checkout currently supports Cash on Delivery. Online payment is intentionally disabled until a payment provider is configured.
- Orders appear in the assigned branch's Orders section and in the Super Admin's network-wide orders. Customers can view status history on the Shop page under My Orders.
- Order status updates create customer notifications. Cancellation restores the ordered quantity to branch stock.
- In-app notification records are stored in PostgreSQL. Phone delivery is optional and requires Twilio credentials in backend/.env: `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_SMS_FROM`; optionally `TWILIO_WHATSAPP_FROM` and `PHARMA360_ADMIN_ALERT_PHONE`. Customer SMS/WhatsApp is opt-in at checkout and also respects saved notification preferences. Branch SMS is sent to the branch phone when Twilio SMS is configured.
- Existing database tables are preserved. Backend startup applies additive columns for customer order details and branch coordinates; no database reset is performed.

## Resumed audit changes

- WhatsApp manual testing is opt-in and will not send a message during pytest collection.
- Order status updates use row locking where supported and stricter branch checks.
- Super Admin can provision delivery partners for an active branch; assignments are validated against the order's branch.
- The Orders UI restricts status actions to valid workflow transitions.
- Backend test command: `cd backend && python -m pytest -q`.
- Frontend build command: `cd frontend && npm ci && npm run build` (requires a complete npm installation).

See `docs/IMPLEMENTATION_STATUS.md` for the current verification results and known limitations.

inventory login:
Login URL: http://localhost:5173/inventory/login
banjarahillsinventory@gmail.com 
password:banjarahills@12345