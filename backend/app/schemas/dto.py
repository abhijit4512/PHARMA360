from pydantic import BaseModel, Field
from datetime import date

class LoginIn(BaseModel):
    # Accept development-only domains such as .local used by seeded demo accounts.
    email: str = Field(min_length=3, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    password: str

class PharmacyIn(BaseModel):
    name: str = Field(min_length=2)
    email: str = Field(min_length=3, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    phone: str = ""
    address: str = ""
    city: str = ""
    latitude: float | None = None
    longitude: float | None = None
    license_number: str = ""
    gst_number: str = ""
    owner_name: str = "Store Owner"
    password: str = Field(min_length=8)

class ProductIn(BaseModel):
    sku: str
    name: str
    generic_name: str = ""
    brand: str = ""
    category: str
    description: str = ""
    mrp: float = Field(ge=0)
    selling_price: float = Field(ge=0)
    prescription_required: bool = False
    image_url: str = ""

class BatchIn(BaseModel):
    pharmacy_id: int | None = None
    product_id: int
    batch_number: str
    quantity: int = Field(ge=0)
    purchase_price: float = Field(ge=0)
    expiry_date: date | None = None

class OrderIn(BaseModel):
    pharmacy_id: int
    customer_name: str = ""
    customer_email: str = ""
    customer_phone: str = Field(min_length=7, max_length=30)
    delivery_address: str = ""
    fulfillment_type: str = "delivery"
    delivery_notes: str = ""
    payment_method: str = "COD"
    sms_opt_in: bool = False
    whatsapp_opt_in: bool = False
    items: list[dict]

class ExpenseIn(BaseModel):
    category: str
    description: str = ""
    amount: float = Field(gt=0)


class CustomerRegisterIn(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    email: str = Field(min_length=3, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    phone: str = ""
    password: str = Field(min_length=8)

class NotificationPreferencesIn(BaseModel):
    email_enabled: bool = True
    sms_enabled: bool = False
    whatsapp_enabled: bool = False
    order_updates: bool = True
    offers_enabled: bool = False


class CustomerAdminUpdateIn(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=160)
    phone: str | None = Field(default=None, max_length=30)
    is_active: bool | None = None

class DeliveryPartnerIn(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    phone: str = Field(min_length=7, max_length=30)
    email: str = ""
    is_active: bool = True
    pharmacy_id: int | None = None  # Required for Super Admin provisioning; ignored for branch users.

class DeliveryAssignmentIn(BaseModel):
    order_id: int
    partner_id: int
    notes: str = ""

class DeliveryStatusIn(BaseModel):
    status: str
    failed_reason: str = ""
    notes: str = ""
