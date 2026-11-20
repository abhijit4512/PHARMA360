from app.core.database import Base, engine, SessionLocal
from app.core.security import hash_password
from app.core.config import settings
from app.models.entities import User, Pharmacy, Product, InventoryBatch, Order, OrderItem, Expense
from datetime import date, datetime, timedelta
from sqlalchemy import inspect, text

Base.metadata.create_all(bind=engine)
# Safe additive migration for existing databases so seeding can run before API startup.
inspector=inspect(engine)
seed_additions={'orders':{'customer_user_id':'INTEGER','customer_phone':"VARCHAR(30) DEFAULT ''",'delivery_address':"TEXT DEFAULT ''",'fulfillment_type':"VARCHAR(30) DEFAULT 'delivery'",'delivery_notes':"TEXT DEFAULT ''"},'pharmacies':{'latitude':'FLOAT','longitude':'FLOAT'},'users':{'phone':"VARCHAR(30) DEFAULT ''"}}
for table,columns in seed_additions.items():
    present={col['name'] for col in inspector.get_columns(table)}
    for col,ddl in columns.items():
        if col not in present:
            with engine.begin() as conn: conn.execute(text(f'ALTER TABLE {table} ADD COLUMN {col} {ddl}'))
db=SessionLocal()
try:
    if not db.query(User).filter(User.email==settings.superadmin_email).first():
        db.add(User(name='PHARMA360 Super Admin',email=settings.superadmin_email,password_hash=hash_password(settings.superadmin_password),role='super_admin'))
    if db.query(Pharmacy).count()==0:
        stores=[Pharmacy(name='CarePlus Pharmacy – Banjara Hills',email='banjara@pharma360.local',phone='+91 98765 10001',city='Hyderabad',address='Road No. 12, Banjara Hills',license_number='DL-HYD-001',latitude=17.4126,longitude=78.4482),Pharmacy(name='Wellness Pharmacy – Madhapur',email='madhapur@pharma360.local',phone='+91 98765 10002',city='Hyderabad',address='Hitech City Road, Madhapur',license_number='DL-HYD-002',latitude=17.4483,longitude=78.3915),Pharmacy(name='HealthFirst Pharmacy – Kukatpally',email='kukatpally@pharma360.local',phone='+91 98765 10003',city='Hyderabad',address='KPHB, Kukatpally',license_number='DL-HYD-003',latitude=17.4933,longitude=78.3996)]
        db.add_all(stores); db.flush()
        for i,s in enumerate(stores): db.add(User(name=f'{s.name} Manager',email=s.email,password_hash=hash_password('StoreDemo123!'),role='pharmacy_owner',pharmacy_id=s.id))
    # Approximate neighborhood coordinates for demo stores only; Super Admin can edit exact pin locations in Store management.
    demo_locations={'banjara@pharma360.local':(17.4126,78.4482),'madhapur@pharma360.local':(17.4483,78.3915),'kukatpally@pharma360.local':(17.4933,78.3996)}
    for email,coords in demo_locations.items():
        store=db.query(Pharmacy).filter_by(email=email).first()
        if store and (store.latitude is None or store.longitude is None): store.latitude,store.longitude=coords

    if db.query(Product).filter(Product.sku.like('P360-%')).count() < 200:
        catalog = {
          "OTC & Everyday Care": ["Oral Rehydration Salts", "Antacid Chewable Tablets", "Cough Lozenges", "Saline Nasal Spray", "Digital Thermometer", "Hot Water Bag", "Adhesive Bandages", "Cotton Roll", "Hand Sanitizer", "Face Mask Pack"],
          "Pain Relief": ["Paracetamol 500 mg", "Paracetamol 650 mg", "Ibuprofen 200 mg", "Pain Relief Gel", "Cold Compress Pack", "Hot Compress Pack", "Muscle Rub Balm", "Pain Relief Spray", "Wheat Heat Pack", "Pain Relief Patch"],
          "Allergy Care": ["Cetirizine 10 mg", "Loratadine 10 mg", "Fexofenadine 120 mg", "Saline Nasal Drops", "Allergy Eye Lubricant", "Dust Mask Pack", "Air Purifier Filter", "Nasal Wash Kit", "Hypoallergenic Lotion", "Allergy Care Pack"],
          "Diabetes Care": ["Glucometer Starter Kit", "Blood Glucose Test Strips", "Lancets Pack", "Alcohol Swabs", "Insulin Cooler Bag", "Diabetes Foot Cream", "Sugar-Free Nutrition Powder", "Diabetes Logbook", "Glucose Tablets", "Medical Alert Bracelet"],
          "Cardiac Care": ["Digital BP Monitor", "BP Monitor Cuff", "Pill Organizer Weekly", "Pulse Oximeter", "Compression Socks", "Heart Health Logbook", "Walking Support Cane", "Electrolyte Drink Mix", "Medical Alert Pendant", "BP Monitor Batteries"],
          "Baby Care": ["Baby Gentle Wipes", "Baby Diapers Pack", "Baby Shampoo", "Baby Lotion", "Baby Massage Oil", "Feeding Bottle", "Baby Nasal Aspirator", "Baby Thermometer", "Diaper Rash Cream", "Baby Cotton Buds"],
          "Personal Care": ["Hand Wash", "Body Wash", "Moisturizing Lotion", "Toothbrush Soft", "Toothpaste", "Shampoo", "Conditioner", "Deodorant", "Cotton Pads", "Wet Wipes"],
          "Skin Care": ["Gentle Face Cleanser", "Moisturizer", "Sunscreen SPF 30", "Sunscreen SPF 50", "Lip Balm", "Aloe Gel", "Face Serum", "Body Lotion", "Cleansing Micellar Water", "Skin Care Travel Kit"],
          "Vitamins & Supplements": ["Vitamin C Supplement", "Vitamin D Supplement", "Multivitamin Tablets", "Calcium Supplement", "Vitamin B Complex", "Zinc Supplement", "Omega-3 Supplement", "Iron Supplement", "Electrolyte Powder", "Protein Nutrition Powder"],
          "Medical Devices": ["Digital Thermometer", "Pulse Oximeter", "Digital BP Monitor", "Nebulizer", "Heating Pad", "Weighing Scale", "Glucometer", "Steam Inhaler", "Medical Scissors", "First Aid Kit"],
          "First Aid": ["Adhesive Bandage Pack", "Sterile Gauze Pads", "Medical Tape", "Antiseptic Solution", "Cotton Roll", "Elastic Bandage", "Burn Dressing", "Disposable Gloves", "First Aid Scissors", "First Aid Kit Refill"],
          "Ayurvedic & Herbal": ["Herbal Balm", "Aloe Vera Gel", "Herbal Tea Blend", "Neem Soap", "Herbal Hair Oil", "Turmeric Face Wash", "Herbal Cough Lozenges", "Herbal Digestive Tea", "Herbal Massage Oil", "Herbal Wellness Pack"],
          "Health & Wellness": ["Yoga Mat", "Resistance Band", "Water Bottle", "Fitness Tracker", "Hot Water Bottle", "Sleep Eye Mask", "Ear Plugs", "Wellness Journal", "Foot Massager", "Travel Wellness Kit"],
          "Oral Care": ["Soft Toothbrush", "Electric Toothbrush", "Fluoride Toothpaste", "Mouthwash", "Dental Floss", "Tongue Cleaner", "Denture Care Tablets", "Sensitive Toothpaste", "Interdental Brushes", "Oral Care Travel Kit"],
          "Nutrition": ["Protein Powder", "Nutrition Shake", "Meal Replacement Powder", "Fiber Supplement", "Electrolyte Powder", "Oats Nutrition Pack", "Nutri Bars", "High Protein Drink", "Nutrition Shaker", "Nutrition Starter Pack"],
          "Eye Care": ["Lubricating Eye Drops", "Eye Wash Cup", "Eye Compress", "Lens Cleaning Solution", "Contact Lens Case", "Eye Protection Glasses", "Eye Mask", "Lens Rewetting Drops", "Eye Care Wipes", "Eye Care Travel Kit"],
          "Digestive Care": ["ORS Sachets", "Antacid Tablets", "Digestive Enzyme Supplement", "Fiber Powder", "Probiotic Supplement", "Gas Relief Hot Pack", "Digestive Wellness Tea", "Travel Motion Bands", "Hydration Bottle", "Digestive Care Kit"],
          "Respiratory Care": ["Steam Inhaler", "Nebulizer", "Saline Spray", "Disposable Face Masks", "Spacer Device", "Peak Flow Meter", "Air Filter Mask", "Humidifier", "Nebulizer Tubing", "Respiratory Care Kit"],
          "Women's Health": ["Sanitary Pads", "Panty Liners", "Menstrual Cup", "Heating Pad", "Intimate Wash", "Pregnancy Test Kit", "Period Pain Heat Patch", "Cotton Underwear Pack", "Women's Multivitamin", "Women's Wellness Kit"],
          "Senior Care": ["Walking Cane", "Adult Diapers", "Bed Protector Sheets", "Pill Organizer", "Grab Bar", "Digital BP Monitor", "Anti-Slip Socks", "Reacher Grabber", "Mobility Support Cushion", "Senior Care Kit"]
        }
        rx_categories={"Pain Relief","Allergy Care","Cardiac Care","Diabetes Care","Digestive Care","Respiratory Care"}
        products=[]
        for cat,names in catalog.items():
            for idx,name in enumerate(names,1):
                sku=f"P360-{cat[:3].upper().replace(' ','')}-{idx:02d}"
                base=round(45+idx*17+(len(cat)%9)*4,2)
                products.append(Product(sku=sku,name=name,generic_name=name,brand="PHARMA360 Essentials",category=cat,description="Product information and directions must be reviewed on the manufacturer label. Ask a pharmacist for advice when appropriate.",mrp=base,selling_price=round(base*.9,2),prescription_required=(cat in rx_categories and idx<=4),image_url=""))
        for product in products:
            existing=db.query(Product).filter(Product.sku==product.sku).first()
            if not existing:
                db.add(product)
        db.flush()
    # Seed demo stock independently from catalog creation. This is intentionally
    # idempotent and only inserts missing seed batches; existing inventory is preserved.
    for store in db.query(Pharmacy).all():
        for product in db.query(Product).filter(Product.sku.like('P360-%'), Product.is_active.is_(True)).all():
            batch_no=f"SEED-{store.id}-{product.id:04d}"
            if not db.query(InventoryBatch).filter_by(pharmacy_id=store.id,product_id=product.id,batch_number=batch_no).first():
                db.add(InventoryBatch(pharmacy_id=store.id,product_id=product.id,batch_number=batch_no,quantity=25+(product.id%20),purchase_price=round(product.selling_price*.65,2),expiry_date=date.today()+timedelta(days=365)))
    db.commit()
    print(f'Seed complete. Super Admin: {settings.superadmin_email}; stores: {db.query(Pharmacy).count()}; products: {db.query(Product).count()}')
finally: db.close()
