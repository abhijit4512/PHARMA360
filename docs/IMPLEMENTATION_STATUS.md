# PHARMA360 implementation status — resumed audit

## Existing project retained
- React + TypeScript + Vite frontend; FastAPI + SQLAlchemy backend; PostgreSQL with SQLite fallback.
- Existing users, stores, products, batches, orders, expenses, notifications and seed workflow retained. No database reset or destructive migration performed.
- JWT staff/customer authentication, store provisioning, catalog, inventory batches, customer registration/login, customer checkout, branch selection, COD order placement, order status history, notification preferences, customer directory, delivery assignment screens and KPI summaries are present in the project.

## Changes made during this resumed pass
- Replaced `backend/test_whatsapp.py` with an opt-in manual smoke test. It does not import Twilio or send a message during pytest collection. Explicit environment opt-in and recipient are required to run it manually.
- Order status updates now load the order with `with_for_update()` (effective on databases supporting row-level locks) and reject branch-scoped users without an assigned branch.
- Return inventory batch lookup during reject/cancel now uses a row lock where supported.
- Delivery partner creation now supports Super Admin provisioning for a selected active branch; branch users still create partners only for their own branch.
- Delivery assignment validates that the partner and order belong to the same branch, including for Super Admin assignments.
- Delivery partners can be activated/deactivated; deactivation is blocked while the partner has active assignments.
- Orders UI now offers only valid next status transitions based on the backend state machine.
- Added route-level order workflow tests for acceptance/history, rejection reason/stock restoration, and branch isolation. They are skipped if the required backend JWT dependency is unavailable in the test environment.

## Verification performed
- `python -m pytest -q`: **6 passed**. Route tests call the endpoint functions directly; auth crypto imports are stubbed in this offline environment, so full JWT/auth integration is not verified.
- `python -m compileall -q app`: passed.
- TypeScript/TSX syntax parsing using the globally available TypeScript parser: passed for all frontend source files.
- `npm run build`: currently blocked because the frontend `node_modules` directory is incomplete/corrupt and npm dependency installation timed out in this environment. The TypeScript build has not been fully verified.

## Known limitations / not production-ready
- Frontend full type-check/build could not be completed until dependencies are installed cleanly with `npm ci`/`npm install`.
- Route-level workflow tests need the full backend dependencies (`pip install -r requirements.txt`) to run rather than skip.
- Payment gateway/webhooks, online payments, refunds and COD settlement/reconciliation are not implemented.
- Prescription upload, verification, pharmacist dispensing controls and regulated-medicine fulfillment restrictions are incomplete.
- Supplier procurement, purchase orders, inventory transfer/adjustment and expiry workflows are incomplete.
- Delivery partner portal, live GPS, ETA and proof-of-delivery are incomplete; current delivery workflow is milestone based.
- Complete financial ledger, GST invoices/tax, returns/credit notes, discounts and reconciliation are incomplete.
- Email/push/Telegram provider integrations, durable retry queue and comprehensive notification delivery tracking are incomplete.
- Customer support/complaints, full address book, persisted cart and reviews are incomplete.
- Google ADK/A2A agents are not implemented in this project.
- Security hardening (MFA, refresh-token rotation, rate limiting, audit completeness, secure file storage, PostgreSQL RLS), backups, monitoring, CI/CD and production deployment review remain required.

**Do not use this MVP for live regulated medicine fulfillment or real payments until the missing workflows, applicable Indian legal/compliance requirements, security review and production testing are completed.**
