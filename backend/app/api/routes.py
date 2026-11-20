from datetime import datetime, timedelta, date
from uuid import uuid4
import os
import logging
from app.services.notifications import send_twilio, send_email

logger = logging.getLogger("pharma360.orders")
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.core.database import get_db
from app.core.security import verify_password, create_access_token, get_current_user, require_roles, hash_password
from app.models.entities import User, Pharmacy, Product, InventoryBatch, Order, OrderItem, Expense, AuditLog, NotificationPreference, OrderNotification, OrderStatusHistory, DeliveryPartner, DeliveryAssignment
from app.schemas.dto import LoginIn, PharmacyIn, ProductIn, BatchIn, OrderIn, ExpenseIn, CustomerRegisterIn, NotificationPreferencesIn, CustomerAdminUpdateIn, DeliveryPartnerIn, DeliveryAssignmentIn, DeliveryStatusIn

router = APIRouter(prefix="/api")

@router.post('/auth/login')
def login(payload: LoginIn, db: Session = Depends(get_db)):
    user = db.query(User).filter(func.lower(User.email) == payload.email.lower()).first()
    if not user or not user.is_active or not verify_password(payload.password, user.password_hash):
        raise HTTPException(401, 'Incorrect email or password')
    return {"access_token": create_access_token(user), "token_type": "bearer", "user": {"id": user.id, "name": user.name, "email": user.email, "role": user.role, "pharmacy_id": user.pharmacy_id, "phone": user.phone}}

@router.get('/auth/me')
def me(user: User = Depends(get_current_user)):
    return {"id": user.id, "name": user.name, "email": user.email, "role": user.role, "pharmacy_id": user.pharmacy_id, "phone": user.phone}


@router.post('/auth/customer/register')
def customer_register(payload: CustomerRegisterIn, db: Session = Depends(get_db)):
    email=payload.email.strip().lower()
    if db.query(User).filter(func.lower(User.email)==email).first():
        raise HTTPException(409, 'Email is already registered')
    user=User(name=payload.name.strip(),email=email,password_hash=hash_password(payload.password),role='customer',pharmacy_id=None,phone=payload.phone.strip())
    db.add(user); db.flush()
    db.add(NotificationPreference(user_id=user.id))
    db.commit(); db.refresh(user)
    return {"access_token":create_access_token(user),"token_type":"bearer","user":{"id":user.id,"name":user.name,"email":user.email,"role":user.role,"pharmacy_id":user.pharmacy_id,"phone":user.phone}}

@router.post('/auth/customer/login')
def customer_login(payload: LoginIn, db: Session = Depends(get_db)):
    user=db.query(User).filter(func.lower(User.email)==payload.email.lower(),User.role=='customer').first()
    if not user or not user.is_active or not verify_password(payload.password,user.password_hash):
        raise HTTPException(401,'Incorrect customer email or password')
    return {"access_token":create_access_token(user),"token_type":"bearer","user":{"id":user.id,"name":user.name,"email":user.email,"role":user.role,"pharmacy_id":user.pharmacy_id,"phone":user.phone}}

@router.get('/customers')
def list_customers(q: str|None=None, db: Session=Depends(get_db), user: User=Depends(require_roles('super_admin','pharmacy_owner','pharmacy_manager','accountant','pharmacist'))):
    customers_query=db.query(User).filter(User.role=='customer')
    if user.role!='super_admin':
        branch_order_ids=db.query(Order.customer_user_id).filter(Order.pharmacy_id==user.pharmacy_id,Order.customer_user_id.is_not(None)).distinct()
        customers_query=customers_query.filter(User.id.in_(branch_order_ids))
    if q:
        term=f'%{q.strip()}%'
        customers_query=customers_query.filter((User.name.ilike(term))|(User.email.ilike(term))|(User.phone.ilike(term)))
    customers=customers_query.order_by(User.created_at.desc()).limit(500).all()
    output=[]
    for c in customers:
        order_query=db.query(Order).filter(Order.customer_user_id==c.id)
        if user.role!='super_admin': order_query=order_query.filter(Order.pharmacy_id==user.pharmacy_id)
        customer_orders=order_query.all()
        output.append({'id':c.id,'name':c.name,'email':c.email,'phone':c.phone,'created_at':c.created_at.isoformat(),'is_active':c.is_active,'orders':len(customer_orders),'spending':round(sum(o.total for o in customer_orders if o.status=='delivered'),2),'last_order':max((o.created_at for o in customer_orders),default=None).isoformat() if customer_orders else None})
    return output

@router.get('/customers/{customer_id}')
def customer_detail(customer_id:int,db:Session=Depends(get_db),user:User=Depends(require_roles('super_admin','pharmacy_owner','pharmacy_manager','accountant','pharmacist'))):
    customer=db.get(User,customer_id)
    if not customer or customer.role!='customer': raise HTTPException(404,'Customer not found')
    q=db.query(Order).filter(Order.customer_user_id==customer.id)
    if user.role!='super_admin': q=q.filter(Order.pharmacy_id==user.pharmacy_id)
    orders=q.order_by(Order.created_at.desc()).all()
    return {'id':customer.id,'name':customer.name,'email':customer.email,'phone':customer.phone,'created_at':customer.created_at.isoformat(),'is_active':customer.is_active,'orders':[_order_dict(o,db,True) for o in orders],'total_orders':len(orders),'total_spending':round(sum(o.total for o in orders if o.status=='delivered'),2)}

@router.patch('/customers/{customer_id}')
def update_customer(customer_id:int,payload:CustomerAdminUpdateIn,db:Session=Depends(get_db),user:User=Depends(require_roles('super_admin','pharmacy_owner','pharmacy_manager'))):
    customer=db.get(User,customer_id)
    if not customer or customer.role!='customer': raise HTTPException(404,'Customer not found')
    if user.role!='super_admin' and not db.query(Order.id).filter(Order.customer_user_id==customer.id,Order.pharmacy_id==user.pharmacy_id).first(): raise HTTPException(403,'Customer is outside your branch scope')
    for key,value in payload.model_dump(exclude_unset=True).items(): setattr(customer,key,value)
    db.add(AuditLog(user_id=user.id,action='updated',entity='customer',entity_id=str(customer.id)))
    db.commit(); return {'id':customer.id,'name':customer.name,'phone':customer.phone,'is_active':customer.is_active}

@router.get('/catalog/categories')
def catalog_categories(db: Session = Depends(get_db)):
    return [{"name":name,"product_count":count} for name,count in db.query(Product.category,func.count(Product.id)).filter(Product.is_active.is_(True)).group_by(Product.category).order_by(Product.category).all()]

@router.get('/catalog/products')
def public_catalog_products(category: str|None=None, q: str|None=None, db: Session=Depends(get_db)):
    query=db.query(Product).filter(Product.is_active.is_(True))
    if category: query=query.filter(Product.category==category)
    if q: query=query.filter((Product.name.ilike(f'%{q}%')) | (Product.brand.ilike(f'%{q}%')) | (Product.generic_name.ilike(f'%{q}%')))
    rows=query.order_by(Product.category,Product.name).all()
    return [{"id":p.id,"sku":p.sku,"name":p.name,"generic_name":p.generic_name,"brand":p.brand,"category":p.category,"description":p.description,"mrp":p.mrp,"selling_price":p.selling_price,"prescription_required":p.prescription_required,"image_url":p.image_url,"stock":int(db.query(func.sum(InventoryBatch.quantity)).filter(InventoryBatch.product_id==p.id).scalar() or 0)} for p in rows]

@router.get('/catalog/branches')
def catalog_branches(city: str|None=None, product_ids: str|None=None, product_quantities: str|None=None, db: Session=Depends(get_db)):
    ids=[]; required={}
    if product_ids:
        try: ids=[int(v) for v in product_ids.split(',') if v.strip()]
        except ValueError: raise HTTPException(400,'Invalid product IDs')
    if product_quantities:
        try: required={int(pair.split(':')[0]):int(pair.split(':')[1]) for pair in product_quantities.split(',') if pair}
        except (ValueError,IndexError): raise HTTPException(400,'Invalid product quantities')
    branches=db.query(Pharmacy).filter(Pharmacy.status=='active').order_by(Pharmacy.city,Pharmacy.name).all()
    result=[]
    for branch in branches:
        stock_rows=db.query(InventoryBatch.product_id,func.sum(InventoryBatch.quantity)).filter(InventoryBatch.pharmacy_id==branch.id,InventoryBatch.quantity>0).group_by(InventoryBatch.product_id).all()
        stock={int(pid):int(qty or 0) for pid,qty in stock_rows}
        can_fulfill=all(stock.get(pid,0)>=required.get(pid,1) for pid in ids)
        city_text=(city or '').strip().lower(); branch_text=(str(branch.city or '')+' '+str(branch.address or '')).lower(); city_match=bool(city_text and (city_text in branch_text or (branch.city or '').lower() in city_text))
        result.append({'id':branch.id,'name':branch.name,'city':branch.city,'address':branch.address,'phone':branch.phone,'latitude':branch.latitude,'longitude':branch.longitude,'stock_by_product':stock,'can_fulfill':can_fulfill,'city_match':city_match})
    result.sort(key=lambda b:(not b['city_match'],not b['can_fulfill'],b['name']))
    return result

@router.get('/notifications/preferences')
def get_notification_preferences(user: User=Depends(require_roles('customer')),db:Session=Depends(get_db)):
    pref=db.query(NotificationPreference).filter_by(user_id=user.id).first()
    if not pref:
        pref=NotificationPreference(user_id=user.id);db.add(pref);db.commit();db.refresh(pref)
    return {k:getattr(pref,k) for k in ['email_enabled','sms_enabled','whatsapp_enabled','order_updates','offers_enabled']}

@router.put('/notifications/preferences')
def update_notification_preferences(payload: NotificationPreferencesIn,user:User=Depends(require_roles('customer')),db:Session=Depends(get_db)):
    pref=db.query(NotificationPreference).filter_by(user_id=user.id).first()
    if not pref: pref=NotificationPreference(user_id=user.id);db.add(pref)
    for key,value in payload.model_dump().items(): setattr(pref,key,value)
    db.commit();return {k:getattr(pref,k) for k in payload.model_dump().keys()}

@router.get('/dashboard/summary')
def dashboard_summary(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    q = db.query(Order)
    if user.role != 'super_admin': q = q.filter(Order.pharmacy_id == user.pharmacy_id)
    orders = q.all()
    pharmacy_count = db.query(Pharmacy).count() if user.role == 'super_admin' else 1
    store_ids = [p.id for p in db.query(Pharmacy.id).all()] if user.role == 'super_admin' else [user.pharmacy_id]
    invq = db.query(InventoryBatch).filter(InventoryBatch.pharmacy_id.in_(store_ids))
    inventory = invq.all()
    expenses = db.query(Expense).filter(Expense.pharmacy_id.in_(store_ids)).all()
    delivered = [o for o in orders if o.status == 'delivered']
    revenue = sum(o.total for o in delivered)
    cogs = db.query(func.sum(OrderItem.unit_cost * OrderItem.quantity)).join(Order, Order.id == OrderItem.order_id).filter(Order.id.in_([o.id for o in delivered])).scalar() or 0
    expense_total = sum(e.amount for e in expenses)
    today = date.today()
    today_orders = [o for o in orders if o.created_at.date() == today]
    low_stock = sum(1 for b in inventory if b.quantity <= 10)
    expiring = sum(1 for b in inventory if b.expiry_date and b.expiry_date <= today + timedelta(days=90) and b.quantity > 0)
    return {"store_count": pharmacy_count, "active_stores": db.query(Pharmacy).filter(Pharmacy.status == 'active').count() if user.role == 'super_admin' else 1,
      "orders": len(orders), "orders_today": len(today_orders), "pending_orders": sum(o.status in ['pending','processing','packed'] for o in orders),
      "delivered_orders": len(delivered), "cod_orders": sum(o.payment_method == 'COD' for o in orders), "paid_orders": sum(o.payment_status == 'paid' for o in orders),
      "revenue": round(revenue,2), "gross_profit": round(revenue-float(cogs),2), "expenses": round(expense_total,2), "net_profit": round(revenue-float(cogs)-expense_total,2),
      "products": db.query(Product).filter(Product.is_active.is_(True)).count(), "stock_units": sum(b.quantity for b in inventory), "low_stock": low_stock, "expiring_batches": expiring,
      "inventory_value": round(sum(b.quantity*b.purchase_price for b in inventory),2),
      "monthly_sales": _monthly_sales(orders)}

def _monthly_sales(orders):
    months = []
    now = datetime.now()
    for offset in range(5,-1,-1):
        month = (now.month - 1 - offset) % 12 + 1
        year = now.year + (now.month - 1 - offset) // 12
        amount = sum(o.total for o in orders if o.status == 'delivered' and o.created_at.year == year and o.created_at.month == month)
        months.append({"month": datetime(year, month, 1).strftime('%b'), "revenue": round(amount,2)})
    return months

@router.get('/stores')
def list_stores(db: Session = Depends(get_db), user: User = Depends(require_roles('super_admin'))):
    stores = db.query(Pharmacy).order_by(Pharmacy.id.desc()).all()
    result=[]
    for s in stores:
        orders=db.query(Order).filter(Order.pharmacy_id==s.id).all()
        result.append({"id":s.id,"name":s.name,"email":s.email,"phone":s.phone,"city":s.city,"address":s.address,"latitude":s.latitude,"longitude":s.longitude,"status":s.status,"orders":len(orders),"sales":round(sum(o.total for o in orders if o.status=='delivered'),2)})
    return result

@router.post('/stores')
def create_store(payload: PharmacyIn, db: Session = Depends(get_db), user: User = Depends(require_roles('super_admin'))):
    if db.query(User).filter(User.email == payload.email).first() or db.query(Pharmacy).filter(Pharmacy.email == payload.email).first(): raise HTTPException(409,'Email already exists')
    store=Pharmacy(name=payload.name,email=payload.email,phone=payload.phone,address=payload.address,city=payload.city,latitude=payload.latitude,longitude=payload.longitude,license_number=payload.license_number,gst_number=payload.gst_number)
    db.add(store); db.flush()
    db.add(User(name=payload.owner_name,email=payload.email,password_hash=hash_password(payload.password),role='pharmacy_owner',pharmacy_id=store.id))
    db.add(AuditLog(user_id=user.id,action='created',entity='pharmacy',entity_id=str(store.id)))
    db.commit(); db.refresh(store)
    return {"id":store.id,"name":store.name,"email":store.email,"status":store.status}

@router.patch('/stores/{store_id}/location')
def update_store_location(store_id:int, latitude:float, longitude:float, db:Session=Depends(get_db), user:User=Depends(require_roles('super_admin'))):
    if not (-90<=latitude<=90 and -180<=longitude<=180): raise HTTPException(400,'Invalid coordinates')
    store=db.get(Pharmacy,store_id)
    if not store: raise HTTPException(404,'Store not found')
    store.latitude=latitude; store.longitude=longitude; db.commit()
    return {'id':store.id,'latitude':store.latitude,'longitude':store.longitude}

@router.patch('/stores/{store_id}/status')
def update_store_status(store_id:int, status:str, db:Session=Depends(get_db), user:User=Depends(require_roles('super_admin'))):
    store=db.get(Pharmacy,store_id)
    if not store: raise HTTPException(404,'Store not found')
    if status not in ['active','inactive']: raise HTTPException(400,'Invalid status')
    store.status=status
    db.commit(); return {"id":store.id,"status":store.status}

@router.get('/products')
def products(db:Session=Depends(get_db), user:User=Depends(get_current_user)):
    items=db.query(Product).filter(Product.is_active.is_(True)).order_by(Product.name).all()
    result=[]
    for p in items:
        q=db.query(func.sum(InventoryBatch.quantity)).filter(InventoryBatch.product_id==p.id)
        if user.role!='super_admin': q=q.filter(InventoryBatch.pharmacy_id==user.pharmacy_id)
        result.append({"id":p.id,"sku":p.sku,"name":p.name,"generic_name":p.generic_name,"brand":p.brand,"category":p.category,"mrp":p.mrp,"selling_price":p.selling_price,"prescription_required":p.prescription_required,"image_url":p.image_url,"stock":int(q.scalar() or 0)})
    return result

@router.post('/products')
def create_product(payload:ProductIn, db:Session=Depends(get_db), user:User=Depends(require_roles('super_admin','pharmacy_owner','pharmacy_manager'))):
    if db.query(Product).filter(Product.sku==payload.sku).first(): raise HTTPException(409,'SKU already exists')
    p=Product(**payload.model_dump()); db.add(p); db.commit(); db.refresh(p)
    return {"id":p.id,"name":p.name,"sku":p.sku}

@router.get('/inventory')
def inventory(db:Session=Depends(get_db), user:User=Depends(get_current_user)):
    q=db.query(InventoryBatch)
    if user.role!='super_admin': q=q.filter(InventoryBatch.pharmacy_id==user.pharmacy_id)
    rows=q.all()
    return [{"id":b.id,"pharmacy_id":b.pharmacy_id,"product_id":b.product_id,"product":b.product.name,"batch_number":b.batch_number,"quantity":b.quantity,"purchase_price":b.purchase_price,"expiry_date":b.expiry_date.isoformat() if b.expiry_date else None} for b in rows]

@router.post('/inventory/batches')
def add_batch(payload:BatchIn, db:Session=Depends(get_db), user:User=Depends(require_roles('super_admin','pharmacy_owner','pharmacy_manager','inventory_manager'))):
    pharmacy_id = payload.pharmacy_id if user.role == 'super_admin' else user.pharmacy_id
    if not pharmacy_id: raise HTTPException(400,'A pharmacy must be selected')
    if not db.get(Pharmacy, pharmacy_id): raise HTTPException(404,'Pharmacy not found')
    if not db.get(Product,payload.product_id): raise HTTPException(404,'Product not found')
    values = payload.model_dump(exclude={'pharmacy_id'})
    b=InventoryBatch(pharmacy_id=pharmacy_id,**values); db.add(b); db.commit(); db.refresh(b)
    return {"id":b.id,"quantity":b.quantity}

def _order_dict(order: Order, db: Session, include_items: bool=False):
    pharmacy=db.get(Pharmacy,order.pharmacy_id)
    result={'id':order.id,'order_number':order.order_number,'pharmacy_id':order.pharmacy_id,'pharmacy_name':pharmacy.name if pharmacy else '', 'customer_name':order.customer_name,'customer_email':order.customer_email,'customer_phone':order.customer_phone,'delivery_address':order.delivery_address,'fulfillment_type':order.fulfillment_type,'delivery_notes':order.delivery_notes,'total':order.total,'status':order.status,'payment_method':order.payment_method,'payment_status':order.payment_status,'rejection_reason':order.rejection_reason or '', 'created_at':order.created_at.isoformat()}
    if include_items:
        history=db.query(OrderStatusHistory).filter_by(order_id=order.id).order_by(OrderStatusHistory.created_at.asc()).all()
        result['status_history']=[{'from':h.previous_status,'to':h.new_status,'note':h.note,'created_at':h.created_at.isoformat()} for h in history]
        items=db.query(OrderItem).filter(OrderItem.order_id==order.id).all()
        result['items']=[{'product_id':it.product_id,'name':(db.get(Product,it.product_id).name if db.get(Product,it.product_id) else 'Product'),'quantity':it.quantity,'unit_price':it.unit_price,'line_total':round(it.quantity*it.unit_price,2)} for it in items]
    return result


def _notification_record(db: Session, *, title: str, message: str, order: Order, channel: str, status: str, user_id: int|None=None, pharmacy_id: int|None=None):
    db.add(OrderNotification(user_id=user_id, pharmacy_id=pharmacy_id, order_id=order.id, title=title, message=message, channel=channel, delivery_status=status))


def _notify_order(db: Session, order: Order, title: str, message: str, customer: User|None=None, branch: Pharmacy|None=None):
    """Create in-app notices and send opted-in external messages after order persistence."""
    variables = {"1": order.order_number, "2": f"{order.total:.2f}", "3": branch.name if branch else "PHARMA360"}
    if customer:
        _notification_record(db, title=title, message=message, order=order, channel='in_app', status='created', user_id=customer.id)
        pref=db.query(NotificationPreference).filter_by(user_id=customer.id).first()
        if pref and pref.order_updates:
            if pref.sms_enabled and customer.phone:
                status=send_twilio(customer.phone,message,'sms')
                _notification_record(db,title=title,message=message,order=order,channel='sms',status=status,user_id=customer.id)
            if pref.whatsapp_enabled and customer.phone:
                logger.info("Order %s: triggering customer WhatsApp notification to opted-in customer", order.order_number)
                status=send_twilio(customer.phone,message,'whatsapp',variables)
                _notification_record(db,title=title,message=message,order=order,channel='whatsapp',status=status,user_id=customer.id)
                logger.info("Order %s: customer WhatsApp result=%s", order.order_number, status)
            else:
                logger.info("Order %s: customer WhatsApp skipped (enabled=%s, phone_present=%s)", order.order_number, bool(pref.whatsapp_enabled), bool(customer.phone))
        else:
            logger.info("Order %s: external customer notifications skipped (preference missing or order_updates disabled)", order.order_number)
        if pref and pref.order_updates and pref.email_enabled and customer.email:
            email_status=send_email(customer.email,title,message)
            _notification_record(db,title=title,message=message,order=order,channel='email',status=email_status,user_id=customer.id)
    if branch:
        # Dashboard notifications are created for active staff in the assigned branch only.
        store_users=db.query(User).filter(User.pharmacy_id==branch.id,User.is_active.is_(True)).all()
        for store_user in store_users:
            _notification_record(db,title=title,message=message,order=order,channel='in_app',status='created',user_id=store_user.id,pharmacy_id=branch.id)
        superadmins=db.query(User).filter(User.role=='super_admin',User.is_active.is_(True)).all()
        for admin_user in superadmins:
            _notification_record(db,title=title,message=message,order=order,channel='in_app',status='created',user_id=admin_user.id,pharmacy_id=branch.id)
        if branch.phone:
            status=send_twilio(branch.phone,message,'sms')
            _notification_record(db,title=title,message=message,order=order,channel='sms',status=status,pharmacy_id=branch.id)
            if os.getenv('PHARMA360_BRANCH_WHATSAPP_ENABLED','false').lower()=='true':
                status=send_twilio(branch.phone,message,'whatsapp',variables)
                _notification_record(db,title=title,message=message,order=order,channel='whatsapp',status=status,pharmacy_id=branch.id)
        admin_phone=os.getenv('PHARMA360_ADMIN_ALERT_PHONE','').strip()
        if admin_phone:
            status=send_twilio(admin_phone,message,'sms')
            _notification_record(db,title=title,message=message,order=order,channel='sms',status=status,pharmacy_id=branch.id)

@router.get('/orders')
def orders(db:Session=Depends(get_db), user:User=Depends(require_roles('super_admin','pharmacy_owner','pharmacy_manager','accountant','pharmacist'))):
    q=db.query(Order).order_by(Order.created_at.desc())
    if user.role!='super_admin': q=q.filter(Order.pharmacy_id==user.pharmacy_id)
    return [_order_dict(o,db,True) for o in q.limit(300).all()]

@router.get('/orders/customer')
def customer_orders(db:Session=Depends(get_db), user:User=Depends(require_roles('customer'))):
    q=db.query(Order).filter(Order.customer_user_id==user.id).order_by(Order.created_at.desc())
    return [_order_dict(o,db,True) for o in q.limit(100).all()]

@router.get('/orders/{order_id}')
def order_detail(order_id:int,db:Session=Depends(get_db),user:User=Depends(get_current_user)):
    order=db.get(Order,order_id)
    if not order: raise HTTPException(404,'Order not found')
    if user.role=='customer' and order.customer_user_id!=user.id: raise HTTPException(403,'This order does not belong to you')
    if user.role not in ['customer','super_admin'] and order.pharmacy_id!=user.pharmacy_id: raise HTTPException(403,'Store isolation violation')
    return _order_dict(order,db,True)

@router.post('/orders')
def create_order(payload:OrderIn, db:Session=Depends(get_db), user:User=Depends(require_roles('customer'))):
    pharmacy_id=payload.pharmacy_id
    branch=db.get(Pharmacy,pharmacy_id)
    if not branch or branch.status!='active': raise HTTPException(404,'Selected pharmacy branch is unavailable')
    if payload.fulfillment_type not in ['delivery','pickup']: raise HTTPException(400,'Invalid fulfillment type')
    if payload.payment_method!='COD': raise HTTPException(400,'Only Cash on Delivery is currently enabled. Online payment will be added after payment gateway setup.')
    if payload.fulfillment_type=='delivery' and not payload.delivery_address.strip(): raise HTTPException(400,'Delivery address is required')
    if not payload.items: raise HTTPException(400,'Cart is empty')
    # Lock stock batches and validate the full cart before reducing stock.
    total=0; item_rows=[]; requested={}
    for item in payload.items:
        try: product_id=int(item['product_id']); qty=int(item['quantity'])
        except (KeyError,TypeError,ValueError): raise HTTPException(400,'Invalid cart item')
        requested[product_id]=requested.get(product_id,0)+qty
    for product_id,qty in requested.items():
        product=db.get(Product,product_id)
        if not product or not product.is_active or qty<1 or qty>50: raise HTTPException(400,'Invalid product or quantity')
        if product.prescription_required: raise HTTPException(400,f'{product.name} requires prescription verification before checkout')
        batches=db.query(InventoryBatch).filter(InventoryBatch.pharmacy_id==pharmacy_id,InventoryBatch.product_id==product.id,InventoryBatch.quantity>0).order_by(InventoryBatch.expiry_date.asc().nullslast()).with_for_update().all()
        if sum(b.quantity for b in batches)<qty: raise HTTPException(409,f'Insufficient stock at {branch.name} for {product.name}. Choose another branch or reduce quantity.')
        total+=product.selling_price*qty; item_rows.append((product,qty,batches))
    pref=db.query(NotificationPreference).filter_by(user_id=user.id).first()
    if not pref: pref=NotificationPreference(user_id=user.id); db.add(pref)
    if payload.sms_opt_in: pref.sms_enabled=True
    if payload.whatsapp_opt_in: pref.whatsapp_enabled=True
    db.flush()
    user.phone=payload.customer_phone.strip()
    order=Order(order_number='P360-'+uuid4().hex[:10].upper(),pharmacy_id=pharmacy_id,customer_user_id=user.id,customer_name=user.name,customer_email=user.email,customer_phone=payload.customer_phone.strip(),delivery_address=payload.delivery_address.strip(),fulfillment_type=payload.fulfillment_type,delivery_notes=payload.delivery_notes.strip(),total=round(total,2),status='pending',payment_method='COD',payment_status='cod_pending')
    db.add(order); db.flush()
    db.add(OrderStatusHistory(order_id=order.id,user_id=user.id,previous_status='',new_status='pending',note='Order placed by customer'))
    for product,qty,batches in item_rows:
        remaining=qty; cost=0
        for batch in batches:
            take=min(batch.quantity,remaining); batch.quantity-=take; cost+=take*batch.purchase_price; remaining-=take
            if remaining==0: break
        db.add(OrderItem(order_id=order.id,product_id=product.id,quantity=qty,unit_price=product.selling_price,unit_cost=cost/qty))
    item_summary=', '.join(f'{product.name} x{qty}' for product,qty,_ in item_rows)
    customer_message=f"PHARMA360 order {order.order_number} placed. {item_summary}. Total ₹{order.total:.2f}. Branch: {branch.name}. Status: Order received."
    branch_message=f"New PHARMA360 order {order.order_number}. {item_summary}. Customer {user.name}, {payload.customer_phone}. Total ₹{order.total:.2f}. Please review and accept."
    db.commit(); db.refresh(order)  # Persist order before external notification attempts.
    logger.info("Order %s saved; beginning customer notification triggers (WhatsApp opt-in=%s)", order.order_number, payload.whatsapp_opt_in)
    _notify_order(db,order,'Order placed',customer_message,user,None)
    # Notify only the branch assigned to this order, plus configured super-admin alerts.
    _notify_order(db,order,'New order received',branch_message,None,branch)
    db.commit(); db.refresh(order)
    return _order_dict(order,db,True)

@router.patch('/orders/{order_id}/status')
def update_order(order_id:int,status:str,reason:str='',db:Session=Depends(get_db),user:User=Depends(require_roles('super_admin','pharmacy_owner','pharmacy_manager','pharmacist'))):
    allowed_transitions={
        'pending':{'accepted','rejected','cancelled'},
        'accepted':{'processing','cancelled'},
        'processing':{'packed','cancelled'},
        'packed':{'shipped','out_for_delivery','cancelled'},
        'shipped':{'out_for_delivery','delivered'},
        'out_for_delivery':{'delivered'},
        'rejected':set(),'cancelled':set(),'delivered':set(),'returned':set(),'refunded':set()
    }
    if status not in allowed_transitions: raise HTTPException(400,'Invalid order status')
    # Lock the order row where supported (PostgreSQL) so concurrent status changes
    # cannot both pass the transition check and duplicate side effects.
    order=db.query(Order).filter(Order.id==order_id).with_for_update().first()
    if not order: raise HTTPException(404,'Order not found')
    if user.role!='super_admin' and (not user.pharmacy_id or order.pharmacy_id!=user.pharmacy_id):
        raise HTTPException(403,'Store isolation violation')
    previous_status=order.status
    if status not in allowed_transitions.get(previous_status,set()): raise HTTPException(409,f'Cannot change order from {previous_status} to {status}')
    if status=='rejected' and not reason.strip(): raise HTTPException(400,'A rejection reason is required')
    if status in ['rejected','cancelled']:
        # Return stock to the original branch, using the original purchase cost.
        for item in db.query(OrderItem).filter(OrderItem.order_id==order.id).all():
            return_batch_number=f'RETURN-{order.order_number}'
            batch=db.query(InventoryBatch).filter(InventoryBatch.pharmacy_id==order.pharmacy_id,InventoryBatch.product_id==item.product_id,InventoryBatch.batch_number==return_batch_number).with_for_update().first()
            if batch: batch.quantity+=item.quantity
            else: db.add(InventoryBatch(pharmacy_id=order.pharmacy_id,product_id=item.product_id,batch_number=return_batch_number,quantity=item.quantity,purchase_price=item.unit_cost,expiry_date=None))
    order.status=status
    if status=='rejected': order.rejection_reason=reason.strip()
    if status=='delivered' and order.payment_method=='COD': order.payment_status='paid'
    db.add(OrderStatusHistory(order_id=order.id,user_id=user.id,previous_status=previous_status,new_status=status,note=reason.strip() if status=='rejected' else ''))
    db.add(AuditLog(user_id=user.id,action='status_changed',entity='order',entity_id=str(order.id)))
    customer=db.get(User,order.customer_user_id) if order.customer_user_id else None
    branch=db.get(Pharmacy,order.pharmacy_id)
    message=f'PHARMA360 order {order.order_number} status updated to {status.replace("_"," ")}.'
    if status=='rejected': message+=f' Reason: {order.rejection_reason}'
    db.commit()
    _notify_order(db,order,'Order status update',message,customer,None)
    db.commit(); return {'id':order.id,'status':order.status,'rejection_reason':order.rejection_reason}

@router.get('/notifications')
def notifications(db:Session=Depends(get_db),user:User=Depends(get_current_user)):
    q=db.query(OrderNotification).order_by(OrderNotification.created_at.desc())
    if user.role=='customer': q=q.filter(OrderNotification.user_id==user.id)
    elif user.role=='super_admin': q=q.filter(OrderNotification.user_id==user.id)
    else: q=q.filter(OrderNotification.pharmacy_id==user.pharmacy_id)
    return [{'id':n.id,'order_id':n.order_id,'title':n.title,'message':n.message,'channel':n.channel,'delivery_status':n.delivery_status,'is_read':n.is_read,'created_at':n.created_at.isoformat()} for n in q.limit(100).all()]

@router.patch('/notifications/{notification_id}/read')
def mark_notification_read(notification_id:int,db:Session=Depends(get_db),user:User=Depends(get_current_user)):
    note=db.get(OrderNotification,notification_id)
    if not note: raise HTTPException(404,'Notification not found')
    if user.role=='customer' and note.user_id!=user.id: raise HTTPException(403,'Not your notification')
    if user.role not in ['customer','super_admin'] and note.pharmacy_id!=user.pharmacy_id: raise HTTPException(403,'Store isolation violation')
    note.is_read=True; db.commit(); return {'id':note.id,'is_read':True}

@router.get('/delivery/summary')
def delivery_summary(db:Session=Depends(get_db),user:User=Depends(require_roles('super_admin','pharmacy_owner','pharmacy_manager'))):
    q=db.query(DeliveryAssignment)
    if user.role!='super_admin': q=q.filter(DeliveryAssignment.pharmacy_id==user.pharmacy_id)
    rows=q.all()
    return {'total':len(rows),'assigned':sum(x.status=='assigned' for x in rows),'picked_up':sum(x.status=='picked_up' for x in rows),'out_for_delivery':sum(x.status=='out_for_delivery' for x in rows),'delivered':sum(x.status=='delivered' for x in rows),'failed':sum(x.status=='failed' for x in rows)}

@router.get('/delivery/partners')
def delivery_partners(db:Session=Depends(get_db),user:User=Depends(require_roles('super_admin','pharmacy_owner','pharmacy_manager'))):
    q=db.query(DeliveryPartner).order_by(DeliveryPartner.name)
    if user.role!='super_admin': q=q.filter(DeliveryPartner.pharmacy_id==user.pharmacy_id)
    return [{'id':p.id,'pharmacy_id':p.pharmacy_id,'name':p.name,'phone':p.phone,'email':p.email,'is_active':p.is_active,'availability':p.availability,'assigned_count':db.query(DeliveryAssignment).filter(DeliveryAssignment.partner_id==p.id,DeliveryAssignment.status.in_(['assigned','picked_up','out_for_delivery'])).count()} for p in q.all()]

@router.post('/delivery/partners')
def create_delivery_partner(payload:DeliveryPartnerIn,db:Session=Depends(get_db),user:User=Depends(require_roles('super_admin','pharmacy_owner','pharmacy_manager'))):
    if user.role=='super_admin':
        pharmacy_id=payload.pharmacy_id
        branch=db.get(Pharmacy,pharmacy_id) if pharmacy_id else None
        if not branch or branch.status!='active': raise HTTPException(400,'Select an active pharmacy branch')
    else:
        if not user.pharmacy_id: raise HTTPException(403,'Your account is not assigned to a branch')
        pharmacy_id=user.pharmacy_id
    partner=DeliveryPartner(pharmacy_id=pharmacy_id,name=payload.name,phone=payload.phone,email=payload.email,is_active=payload.is_active)
    db.add(partner); db.commit(); db.refresh(partner)
    return {'id':partner.id,'name':partner.name,'pharmacy_id':partner.pharmacy_id}

@router.patch('/delivery/partners/{partner_id}/status')
def update_delivery_partner_status(partner_id:int,is_active:bool,db:Session=Depends(get_db),user:User=Depends(require_roles('super_admin','pharmacy_owner','pharmacy_manager'))):
    partner=db.get(DeliveryPartner,partner_id)
    if not partner: raise HTTPException(404,'Delivery partner not found')
    if user.role!='super_admin' and (not user.pharmacy_id or partner.pharmacy_id!=user.pharmacy_id): raise HTTPException(403,'Branch isolation violation')
    if not is_active:
        active_jobs=db.query(DeliveryAssignment).filter(DeliveryAssignment.partner_id==partner.id,DeliveryAssignment.status.in_(['assigned','picked_up','out_for_delivery'])).count()
        if active_jobs: raise HTTPException(409,'Partner has active delivery assignments; finish or reassign them first')
    partner.is_active=is_active
    partner.availability='available' if is_active else 'inactive'
    db.add(AuditLog(user_id=user.id,action='status_changed',entity='delivery_partner',entity_id=str(partner.id)))
    db.commit()
    return {'id':partner.id,'is_active':partner.is_active,'availability':partner.availability}

@router.post('/delivery/assignments')
def assign_delivery(payload:DeliveryAssignmentIn,db:Session=Depends(get_db),user:User=Depends(require_roles('super_admin','pharmacy_owner','pharmacy_manager'))):
    order=db.get(Order,payload.order_id); partner=db.get(DeliveryPartner,payload.partner_id)
    if not order: raise HTTPException(404,'Order not found')
    if not partner or not partner.is_active: raise HTTPException(404,'Active delivery partner not found')
    if partner.pharmacy_id!=order.pharmacy_id: raise HTTPException(409,'Delivery partner must belong to the same branch as the order')
    if user.role!='super_admin' and (not user.pharmacy_id or order.pharmacy_id!=user.pharmacy_id): raise HTTPException(403,'Branch isolation violation')
    if order.status!='packed': raise HTTPException(409,'Order must be packed and ready before assignment')
    existing=db.query(DeliveryAssignment).filter_by(order_id=order.id).first()
    if existing: raise HTTPException(409,'This order already has a delivery assignment')
    previous_order_status=order.status
    assignment=DeliveryAssignment(order_id=order.id,pharmacy_id=order.pharmacy_id,partner_id=partner.id,assigned_by=user.id,notes=payload.notes)
    order.status='shipped'
    db.add(assignment); db.add(OrderStatusHistory(order_id=order.id,user_id=user.id,previous_status=previous_order_status,new_status='shipped',note='Delivery partner assigned'))
    db.commit(); db.refresh(assignment)
    return {'id':assignment.id,'order_id':assignment.order_id,'partner_id':assignment.partner_id,'status':assignment.status}

@router.get('/delivery/assignments')
def delivery_assignments(db:Session=Depends(get_db),user:User=Depends(require_roles('super_admin','pharmacy_owner','pharmacy_manager'))):
    q=db.query(DeliveryAssignment).order_by(DeliveryAssignment.created_at.desc())
    if user.role!='super_admin': q=q.filter(DeliveryAssignment.pharmacy_id==user.pharmacy_id)
    return [{'id':a.id,'order_id':a.order_id,'order_number':db.get(Order,a.order_id).order_number,'customer_name':db.get(Order,a.order_id).customer_name,'pharmacy_name':db.get(Pharmacy,a.pharmacy_id).name if db.get(Pharmacy,a.pharmacy_id) else '', 'pharmacy_id':a.pharmacy_id,'partner_id':a.partner_id,'partner_name':a.partner.name,'partner_phone':a.partner.phone,'status':a.status,'pickup_at':a.pickup_at.isoformat() if a.pickup_at else None,'delivered_at':a.delivered_at.isoformat() if a.delivered_at else None,'failed_reason':a.failed_reason,'notes':a.notes,'created_at':a.created_at.isoformat()} for a in q.all()]

@router.patch('/delivery/assignments/{assignment_id}')
def update_delivery_assignment(assignment_id:int,payload:DeliveryStatusIn,db:Session=Depends(get_db),user:User=Depends(require_roles('super_admin','pharmacy_owner','pharmacy_manager'))):
    allowed={'assigned':{'picked_up','failed'},'picked_up':{'out_for_delivery','failed'},'out_for_delivery':{'delivered','failed'},'delivered':set(),'failed':set()}
    assignment=db.get(DeliveryAssignment,assignment_id)
    if not assignment: raise HTTPException(404,'Assignment not found')
    if user.role!='super_admin' and assignment.pharmacy_id!=user.pharmacy_id: raise HTTPException(403,'Branch isolation violation')
    if payload.status not in allowed.get(assignment.status,set()): raise HTTPException(409,f'Invalid delivery transition {assignment.status} → {payload.status}')
    assignment.status=payload.status; assignment.notes=payload.notes or assignment.notes
    previous_order_status=assignment.order.status
    if payload.status=='picked_up': assignment.pickup_at=datetime.utcnow()
    if payload.status=='out_for_delivery': assignment.order.status='out_for_delivery'
    if payload.status=='delivered': assignment.delivered_at=datetime.utcnow(); assignment.order.status='delivered'; assignment.order.payment_status='paid' if assignment.order.payment_method=='COD' else assignment.order.payment_status
    if payload.status=='failed': assignment.failed_reason=payload.failed_reason.strip()
    new_order_status=assignment.order.status
    db.add(OrderStatusHistory(order_id=assignment.order_id,user_id=user.id,previous_status=previous_order_status,new_status=new_order_status,note=f'Delivery: {payload.status}'))
    db.commit(); return {'id':assignment.id,'status':assignment.status}

@router.post('/expenses')
def add_expense(payload:ExpenseIn,db:Session=Depends(get_db),user:User=Depends(require_roles('super_admin','pharmacy_owner','pharmacy_manager','accountant'))):
    if not user.pharmacy_id: raise HTTPException(400,'Select a store for this expense')
    e=Expense(pharmacy_id=user.pharmacy_id,**payload.model_dump()); db.add(e); db.commit(); db.refresh(e)
    return {"id":e.id,"amount":e.amount}
