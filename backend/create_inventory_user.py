from getpass import getpass
from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models.entities import User, Pharmacy

def main():
    db=SessionLocal()
    try:
        name=input('Inventory staff name: ').strip()
        email=input('Inventory staff email: ').strip().lower()
        password=getpass('Password (min 8 chars): ')
        if len(password)<8:
            raise SystemExit('Password must be at least 8 characters.')
        pharmacy_id=input('Pharmacy ID (required for stock access): ').strip()
        pharmacy_id=int(pharmacy_id)
        if not db.get(Pharmacy,pharmacy_id):
            raise SystemExit('Pharmacy ID does not exist.')
        if db.query(User).filter(User.email==email).first():
            raise SystemExit('This email already exists. No existing user was changed.')
        user=User(name=name,email=email,password_hash=hash_password(password),role='inventory_manager',pharmacy_id=pharmacy_id,is_active=True)
        db.add(user);db.commit()
        print(f'Inventory login created: {email} | pharmacy #{pharmacy_id}')
        print('Login URL: http://localhost:5173/inventory/login')
    finally:
        db.close()

if __name__=='__main__':
    main()
