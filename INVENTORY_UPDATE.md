# PHARMA360 Inventory Dashboard Update

## What changed
- Reworked the existing Inventory page into a dashboard inspired by the supplied reference images: KPI cards, inventory trend chart, stock-by-category chart, low-stock/expiry alerts, batch table, filtering, CSV export, and add-stock modal.
- Existing `/inventory` route remains for the main admin workspace.
- Added a separate Inventory Staff login at `/inventory/login`.
- Inventory staff role is `inventory_manager`; after login, this role is routed to a dedicated inventory-only workspace at `/inventory/workspace`.
- Inventory staff accounts are pharmacy-scoped. Main `super_admin` still has all-pharmacy inventory visibility on the normal admin Inventory page.
- Added a non-destructive helper script for creating inventory staff accounts. It refuses to overwrite existing accounts.
- Updated the inventory list API role allow-list.

## Create an inventory staff account
Run from `PHARMA360/backend` after the backend environment is activated and the database is configured:

```bash
python create_inventory_user.py
```

Enter the name, email, password, and existing Pharmacy ID. The account is assigned the `inventory_manager` role and the selected pharmacy.

## Login URLs
- Main Admin/Store login: `/login`
- Inventory staff login: `/inventory/login`
- Inventory staff dashboard: `/inventory/workspace`

## Notes
- Existing project files and database records were not intentionally deleted or reset. This update is provided as a separate project copy.
- The CSV Import button currently displays a placeholder message; actual CSV import parsing/validation is not wired yet.
- Trend chart uses illustrative trend data; stock totals, category breakdown, alerts, and inventory table are derived from the current inventory API response.
- Supplier information is linked to the existing Stores module rather than introducing a new supplier database model.
- Frontend build could not be completed in this environment because `npm ci` timed out. Backend Python files were syntax-compiled successfully. Real `.env` files were omitted from this updated archive to avoid sharing credentials; configure from the `.env.example` templates.
