from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.database import Base, engine
from app.models import entities  # noqa: F401
from app.api.routes import router
from sqlalchemy import inspect, text

Base.metadata.create_all(bind=engine)

# Additive compatibility migration: preserve existing pharmacy/order records.
def ensure_order_columns():
    inspector = inspect(engine)
    additions = {
        'orders': {
            'customer_user_id': 'INTEGER', 'customer_phone': "VARCHAR(30) DEFAULT ''",
            'delivery_address': "TEXT DEFAULT ''", 'fulfillment_type': "VARCHAR(30) DEFAULT 'delivery'",
            'delivery_notes': "TEXT DEFAULT ''", 'rejection_reason': "TEXT DEFAULT ''",
        },
        'pharmacies': {'latitude': 'FLOAT', 'longitude': 'FLOAT'},
        'users': {'phone': "VARCHAR(30) DEFAULT ''"},

    }
    for table, columns in additions.items():
        existing = {c['name'] for c in inspector.get_columns(table)}
        for name, ddl in columns.items():
            if name not in existing:
                with engine.begin() as conn:
                    conn.execute(text(f'ALTER TABLE {table} ADD COLUMN {name} {ddl}'))
ensure_order_columns()
app = FastAPI(title=settings.app_name, version="1.0.0", description="Multi-store pharmacy business and commerce API")
origins=[x.strip() for x in settings.cors_origins.split(',') if x.strip()]
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_credentials=True, allow_methods=['*'], allow_headers=['*'])
app.include_router(router)

@app.get('/health')
def health(): return {"status":"ok","service":"pharma360-api"}
