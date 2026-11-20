"""Provision PHARMA360 demo admin and customer accounts without deleting data."""
from app.core.database import Base, engine, SessionLocal
from app.core.security import hash_password
from app.core.config import settings
from app.models.entities import User, NotificationPreference

Base.metadata.create_all(bind=engine)
ADMIN_EMAIL = settings.superadmin_email.strip().lower()
ADMIN_PASSWORD = settings.superadmin_password
CUSTOMER_EMAIL = "customer@pharma360.local"
CUSTOMER_PASSWORD = "Customer360!2026"

def upsert_demo_user(db, email, name, password, role, phone=""):
    user = db.query(User).filter(User.email == email).first()
    if user is None:
        user = User(name=name, email=email, password_hash=hash_password(password), role=role, phone=phone, is_active=True)
        db.add(user)
    else:
        # Only demo credentials are intentionally synchronized; all other users are untouched.
        user.name = name
        user.password_hash = hash_password(password)
        user.role = role
        user.is_active = True
        if phone and not user.phone:
            user.phone = phone
    db.flush()
    if role == "customer" and not db.query(NotificationPreference).filter_by(user_id=user.id).first():
        db.add(NotificationPreference(user_id=user.id))
    return user

with SessionLocal() as db:
    upsert_demo_user(db, ADMIN_EMAIL, "PHARMA360 Super Admin", ADMIN_PASSWORD, "super_admin")
    upsert_demo_user(db, CUSTOMER_EMAIL, "PHARMA360 Demo Customer", CUSTOMER_PASSWORD, "customer", "+919000000000")
    db.commit()

print("Demo accounts provisioned (existing business data was preserved).")
print(f"ADMIN: {ADMIN_EMAIL}")
print(f"CUSTOMER: {CUSTOMER_EMAIL}")
print("Customer password: Customer360!2026")
print("Admin password is set from backend/.env SUPERADMIN_PASSWORD.")
