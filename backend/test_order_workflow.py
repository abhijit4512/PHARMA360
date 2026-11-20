from datetime import datetime

import pytest
from fastapi import HTTPException
# The workflow functions are called directly in these tests, so auth crypto is
# stubbed only when optional packages are unavailable in the offline test image.
import sys
import types

if "jose" not in sys.modules:
    try:
        import jose  # noqa: F401
    except ImportError:
        jose_stub = types.ModuleType("jose")
        jose_stub.jwt = types.SimpleNamespace(encode=lambda *a, **k: "", decode=lambda *a, **k: {})
        jose_stub.JWTError = Exception
        sys.modules["jose"] = jose_stub
if "passlib.context" not in sys.modules:
    try:
        import passlib.context  # noqa: F401
    except ImportError:
        passlib_stub = types.ModuleType("passlib")
        context_stub = types.ModuleType("passlib.context")
        context_stub.CryptContext = lambda **kwargs: types.SimpleNamespace(hash=lambda p: p, verify=lambda p, h: p == h)
        passlib_stub.context = context_stub
        sys.modules["passlib"] = passlib_stub
        sys.modules["passlib.context"] = context_stub
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from app.models.entities import Pharmacy, User, Product, Order, OrderItem, InventoryBatch, OrderStatusHistory
from app.api import routes


@pytest.fixture
def db():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = Session()
    try:
        branch = Pharmacy(name="Test Branch", email="branch@test.local", status="active")
        session.add(branch)
        session.flush()
        manager = User(name="Branch Manager", email="manager@test.local", password_hash="unused", role="pharmacy_manager", pharmacy_id=branch.id)
        other_branch = Pharmacy(name="Other Branch", email="other@test.local", status="active")
        session.add(other_branch)
        session.flush()
        outsider = User(name="Other Manager", email="other-manager@test.local", password_hash="unused", role="pharmacy_manager", pharmacy_id=other_branch.id)
        product = Product(sku="TEST-1", name="Test medicine", category="Test", mrp=10, selling_price=8, is_active=True)
        session.add_all([manager, outsider, product])
        session.flush()
        order = Order(order_number="P360-TEST0001", pharmacy_id=branch.id, customer_name="Test Customer", customer_phone="1234567890", total=16, status="pending", payment_method="COD", payment_status="cod_pending", created_at=datetime.utcnow())
        session.add(order)
        session.flush()
        item = OrderItem(order_id=order.id, product_id=product.id, quantity=2, unit_price=8, unit_cost=5)
        depleted_batch = InventoryBatch(pharmacy_id=branch.id, product_id=product.id, batch_number="ORIGINAL", quantity=0, purchase_price=5)
        session.add_all([item, depleted_batch])
        session.commit()
        yield session, manager, outsider, order, product, branch
    finally:
        session.close()
        engine.dispose()


def test_order_acceptance_records_status_history(db, monkeypatch):
    session, manager, _, order, _, _ = db
    monkeypatch.setattr(routes, "_notify_order", lambda *args, **kwargs: None)
    result = routes.update_order(order.id, "accepted", "", session, manager)
    assert result["status"] == "accepted"
    history = session.query(OrderStatusHistory).filter_by(order_id=order.id).all()
    assert [(h.previous_status, h.new_status) for h in history] == [("pending", "accepted")]


def test_rejection_requires_reason_and_restores_stock(db, monkeypatch):
    session, manager, _, order, product, branch = db
    monkeypatch.setattr(routes, "_notify_order", lambda *args, **kwargs: None)
    with pytest.raises(HTTPException) as exc:
        routes.update_order(order.id, "rejected", "", session, manager)
    assert exc.value.status_code == 400

    result = routes.update_order(order.id, "rejected", "Out of stock after verification", session, manager)
    assert result["status"] == "rejected"
    returned = session.query(InventoryBatch).filter_by(
        pharmacy_id=branch.id,
        product_id=product.id,
        batch_number=f"RETURN-{order.order_number}",
    ).one()
    assert returned.quantity == 2
    assert returned.purchase_price == 5


def test_branch_manager_cannot_change_other_branch_order(db, monkeypatch):
    session, _, outsider, order, _, _ = db
    monkeypatch.setattr(routes, "_notify_order", lambda *args, **kwargs: None)
    with pytest.raises(HTTPException) as exc:
        routes.update_order(order.id, "accepted", "", session, outsider)
    assert exc.value.status_code == 403
    assert order.status == "pending"


def test_delivery_partner_must_match_order_branch(db):
    session, manager, _, order, _, branch = db
    from app.models.entities import DeliveryPartner
    from app.schemas.dto import DeliveryAssignmentIn
    order.status = "packed"
    other_branch_partner = DeliveryPartner(pharmacy_id=manager.pharmacy_id + 1, name="Wrong Branch Partner", phone="1234567890", is_active=True)
    session.add(other_branch_partner)
    session.commit()
    with pytest.raises(HTTPException) as exc:
        routes.assign_delivery(DeliveryAssignmentIn(order_id=order.id, partner_id=other_branch_partner.id), session, manager)
    assert exc.value.status_code == 409


def test_partner_cannot_be_deactivated_with_active_assignment(db):
    session, manager, _, order, _, branch = db
    from app.models.entities import DeliveryPartner, DeliveryAssignment
    order.status = "packed"
    partner = DeliveryPartner(pharmacy_id=branch.id, name="Assigned Partner", phone="1234567890", is_active=True, availability="available")
    session.add(partner)
    session.flush()
    assignment = DeliveryAssignment(order_id=order.id, pharmacy_id=branch.id, partner_id=partner.id, assigned_by=manager.id, status="assigned")
    session.add(assignment)
    session.commit()
    with pytest.raises(HTTPException) as exc:
        routes.update_delivery_partner_status(partner.id, False, session, manager)
    assert exc.value.status_code == 409
    assert partner.is_active is True
