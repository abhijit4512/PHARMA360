# PHARMA360 Order System Update

## Included
- Persisted cart with quantity controls and cart drawer.
- Customer checkout with delivery or store pickup, customer phone, address, instructions and COD.
- Branch selector checks each branch's stock for every requested cart quantity.
- Nearest-branch ordering: exact city/area match by default; browser geolocation distance when pharmacy latitude/longitude is configured.
- Branch coordinates can be added during store creation or edited from Pharmacy Stores (pin/location action).
- Orders are associated with the customer account and branch.
- Branch stock is reserved/deducted when an order is placed.
- Customer My Orders view and status tracker.
- Admin/store Orders table includes order items and contact/delivery details, status dropdown, periodic refresh.
- In-app notification records for customer, branch staff and Super Admin.
- Customer order-status notifications on updates.
- Cancellation returns item quantities to the branch's inventory.
- Optional SMS and WhatsApp integrations using Twilio.
- Additive database migration for existing database tables; no reset/delete of existing records.

## Upgrade an existing project
1. Back up the project folder and database.
2. Extract this ZIP and copy the updated project files over your current PHARMA360 project. Keep your existing `backend/.env`.
3. Backend: activate your virtual environment and run `python seed.py`. This applies safe additive schema changes and fills demo stock if the seed logic finds missing batches. It also fills approximate neighborhood coordinates for the three demo Hyderabad branches if those coordinates are blank.
4. Restart backend: `uvicorn app.main:app --reload --port 8000`.
5. Frontend: `npm install` then `npm run dev`.

## SMS / WhatsApp configuration
Add these values to `backend/.env` only if you have a Twilio account and configured senders:

```env
TWILIO_ACCOUNT_SID=your_account_sid
TWILIO_AUTH_TOKEN=your_auth_token
TWILIO_SMS_FROM=+1xxxxxxxxxx
TWILIO_WHATSAPP_FROM=whatsapp:+1xxxxxxxxxx
PHARMA360_ADMIN_ALERT_PHONE=+91xxxxxxxxxx
```

Branch SMS goes to the pharmacy phone stored in Pharmacy Stores. Customer SMS/WhatsApp requires the customer to opt in at checkout and have order updates enabled. Phone delivery status is recorded in the notifications table; when credentials are missing it is recorded as `not_configured`. WhatsApp delivery requires an approved sender/template or the applicable Twilio WhatsApp setup. No credentials are included in this ZIP.

## Nearest branch notes
- Demo branch coordinates are approximate neighborhood pins; edit them from Pharmacy Stores for precise branch locations.
- Browser geolocation is requested only when the customer clicks **Use my location**.
- Branches without coordinates are still selectable and are ranked using city/area match and stock availability.

## Payment
Cash on Delivery is enabled. Online payment is intentionally rejected until Razorpay/other payment gateway integration is configured.
