"""PHARMA360 safe seed/import script.
Imports the provided medicine master and batch CSV files without deleting existing data.
All supplied batch/manufacturer/pricing values are demo data and must be verified.
"""
from app.core.database import Base, engine, SessionLocal
from app.core.security import hash_password
from app.core.config import settings
from app.models.entities import User, Pharmacy, Product, InventoryBatch
from sqlalchemy import inspect, text
from datetime import date, datetime
from pathlib import Path
import csv

Base.metadata.create_all(bind=engine)

# Safe additive migrations retained from the original seed script.
inspector = inspect(engine)
seed_additions = {
    'orders': {
        'customer_user_id': 'INTEGER',
        'customer_phone': "VARCHAR(30) DEFAULT ''",
        'delivery_address': "TEXT DEFAULT ''",
        'fulfillment_type': "VARCHAR(30) DEFAULT 'delivery'",
        'delivery_notes': "TEXT DEFAULT ''",
    },
    'pharmacies': {'latitude': 'FLOAT', 'longitude': 'FLOAT'},
    'users': {'phone': "VARCHAR(30) DEFAULT ''"},
}
for table, columns in seed_additions.items():
    present = {col['name'] for col in inspector.get_columns(table)}
    for column, ddl in columns.items():
        if column not in present:
            with engine.begin() as conn:
                conn.execute(text(f'ALTER TABLE {table} ADD COLUMN {column} {ddl}'))

BACKEND_DIR = Path(__file__).resolve().parent
DATA_DIR = BACKEND_DIR / 'app' / 'data' / 'medicine_import'
MASTER_CSV = DATA_DIR / 'medicine_master_500.csv'
BATCH_CSV = DATA_DIR / 'batch_inventory_1000.csv'


def clean(value):
    return (value or '').strip()


def number(value, default=0.0):
    try:
        return float(clean(value).replace(',', ''))
    except (TypeError, ValueError):
        return default


def integer(value, default=0):
    try:
        return int(float(clean(value)))
    except (TypeError, ValueError):
        return default


def truthy(value):
    return clean(value).lower() in {'yes', 'true', '1', 'required', 'rx'}


def parse_date(value):
    value = clean(value)
    if not value:
        return None
    try:
        return date.fromisoformat(value[:10])
    except ValueError:
        return None


def read_csv_rows(path):
    if not path.exists():
        raise FileNotFoundError(
            f'Missing dataset: {path}\nPlace the CSV files inside backend/data/medicine_import/'
        )
    with path.open('r', encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))


db = SessionLocal()
try:
    # Create admin only if it does not already exist.
    if not db.query(User).filter(User.email == settings.superadmin_email).first():
        db.add(User(
            name='PHARMA360 Super Admin',
            email=settings.superadmin_email,
            password_hash=hash_password(settings.superadmin_password),
            role='super_admin',
        ))

    # Create demo pharmacies only when the database has none (preserves existing stores).
    if db.query(Pharmacy).count() == 0:
        stores = [
            Pharmacy(name='CarePlus Pharmacy – Banjara Hills', email='banjara@pharma360.local',
                    phone='+91 98765 10001', city='Hyderabad', address='Road No. 12, Banjara Hills',
                    license_number='DL-HYD-001', latitude=17.4126, longitude=78.4482),
            Pharmacy(name='Wellness Pharmacy – Madhapur', email='madhapur@pharma360.local',
                    phone='+91 98765 10002', city='Hyderabad', address='Hitech City Road, Madhapur',
                    license_number='DL-HYD-002', latitude=17.4483, longitude=78.3915),
            Pharmacy(name='HealthFirst Pharmacy – Kukatpally', email='kukatpally@pharma360.local',
                    phone='+91 98765 10003', city='Hyderabad', address='KPHB, Kukatpally',
                    license_number='DL-HYD-003', latitude=17.4933, longitude=78.3996),
        ]
        db.add_all(stores)
        db.flush()
        for store in stores:
            db.add(User(name=f'{store.name} Manager', email=store.email,
                        password_hash=hash_password('StoreDemo123!'), role='pharmacy_owner',
                        pharmacy_id=store.id))

    demo_locations = {
        'banjara@pharma360.local': (17.4126, 78.4482),
        'madhapur@pharma360.local': (17.4483, 78.3915),
        'kukatpally@pharma360.local': (17.4933, 78.3996),
    }
    for email, coords in demo_locations.items():
        store = db.query(Pharmacy).filter_by(email=email).first()
        if store and (store.latitude is None or store.longitude is None):
            store.latitude, store.longitude = coords

    # Import medicine master CSV. SKU is the stable matching key.
    master_rows = read_csv_rows(MASTER_CSV)
    sku_to_product = {}
    inserted_products = 0
    updated_products = 0

    for row in master_rows:
        sku = clean(row.get('SKU'))
        if not sku:
            continue

        product = db.query(Product).filter(Product.sku == sku).first()
        brand = clean(row.get('Brand_Name'))
        generic = clean(row.get('Generic_Name'))
        strength = clean(row.get('Strength'))
        dosage_form = clean(row.get('Dosage_Form'))
        name_parts = [generic, strength, dosage_form]
        display_name = ' '.join(part for part in name_parts if part).strip()
        if not display_name:
            display_name = brand or sku

        category = clean(row.get('Category')) or 'Uncategorized'
        description_parts = [
            f"Salt/Composition: {clean(row.get('Salt_Composition'))}",
            f"Strength: {strength}",
            f"Dosage form: {dosage_form}",
            f"Pack size: {clean(row.get('Pack_Size'))}",
            f"Manufacturer: {clean(row.get('Manufacturer'))}",
            f"Storage: {clean(row.get('Storage_Conditions'))}",
            f"Dataset quality: {clean(row.get('Data_Quality'))}",
        ]
        description = ' | '.join(part for part in description_parts if not part.endswith(': '))

        mrp = number(row.get('MRP_INR'))
        selling = number(row.get('Selling_Price_INR_DEMO'), mrp)
        if product is None:
            product = Product(
                sku=sku,
                name=display_name[:220],
                generic_name=(generic or display_name)[:220],
                brand=(brand or 'Generic / Unbranded')[:120],
                category=category[:100],
                description=description,
                mrp=mrp,
                selling_price=selling,
                prescription_required=truthy(row.get('Prescription_Required')),
                image_url='',
                is_active=clean(row.get('Product_Status')).lower() not in {'inactive', 'discontinued'},
            )
            db.add(product)
            inserted_products += 1
        else:
            # Update only fields represented by this CSV; keep product IDs and unrelated data.
            product.name = display_name[:220]
            product.generic_name = (generic or display_name)[:220]
            product.brand = (brand or product.brand or 'Generic / Unbranded')[:120]
            product.category = category[:100]
            product.description = description
            product.mrp = mrp
            product.selling_price = selling
            product.prescription_required = truthy(row.get('Prescription_Required'))
            product.is_active = clean(row.get('Product_Status')).lower() not in {'inactive', 'discontinued'}
            updated_products += 1
        sku_to_product[sku] = product

    db.flush()  # assign product IDs before importing batches

    # Import batch data into the first existing pharmacy. Do not duplicate batches.
    batch_rows = read_csv_rows(BATCH_CSV)
    stores = db.query(Pharmacy).order_by(Pharmacy.id).all()
    if not stores:
        raise RuntimeError('No pharmacy/store exists; unable to attach inventory batches.')
    target_store = stores[0]
    inserted_batches = 0
    skipped_batches = 0

    for row in batch_rows:
        sku = clean(row.get('SKU'))
        batch_number = clean(row.get('Batch_Number'))
        product = sku_to_product.get(sku) or db.query(Product).filter(Product.sku == sku).first()
        if not product or not batch_number:
            skipped_batches += 1
            continue

        existing = db.query(InventoryBatch).filter_by(
            pharmacy_id=target_store.id,
            product_id=product.id,
            batch_number=batch_number,
        ).first()
        if existing:
            skipped_batches += 1
            continue

        expiry = parse_date(row.get('Expiry_Date_DEMO'))
        qty = max(0, integer(row.get('Current_Stock_DEMO')))
        purchase_price = number(row.get('Purchase_Price_INR_DEMO'))
        db.add(InventoryBatch(
            pharmacy_id=target_store.id,
            product_id=product.id,
            batch_number=batch_number,
            quantity=qty,
            purchase_price=purchase_price,
            expiry_date=expiry,
        ))
        inserted_batches += 1

    db.commit()
    print('PHARMA360 CSV seed/import completed successfully.')
    print(f'CSV master rows read: {len(master_rows)}')
    print(f'Products inserted: {inserted_products}; products updated by SKU: {updated_products}')
    print(f'CSV batch rows read: {len(batch_rows)}')
    print(f'Inventory batches inserted: {inserted_batches}; skipped (duplicate/missing match): {skipped_batches}')
    print(f'Inventory batches imported into: {target_store.name} (ID {target_store.id})')
    print(f'Total stores: {db.query(Pharmacy).count()} | Total products: {db.query(Product).count()}')
    print('WARNING: Imported CSV batch/manufacturer/pricing details are synthetic demo data; verify before real use.')
finally:
    db.close()
