# PHARMA360 Customer + Branch Notifications (Twilio)

## Notification flow

1. Customer submits checkout with a selected `pharmacy_id` and notification opt-ins.
2. Backend validates stock, creates the order, reduces stock, and commits the order first.
3. Backend writes customer in-app notification; SMS/WhatsApp are attempted only if customer has enabled order updates and the channel.
4. Backend writes in-app notifications to active users belonging to the **assigned branch only**.
5. Backend attempts SMS to the assigned branch phone (if configured). Optional branch WhatsApp can be enabled with `PHARMA360_BRANCH_WHATSAPP_ENABLED=true`.
6. Notifications are saved in `order_notifications`, including `created`, `queued`, `sent`, `failed`, or `not_configured` statuses. A provider failure does not undo the order.
7. Branch users see their alerts in the Orders page notification panel; the customer sees in-app alerts in My Orders/Notifications.

## Twilio setup

1. Create/sign in to Twilio: https://console.twilio.com/
2. Copy Account SID and Auth Token. Keep both secret.
3. For SMS, configure a Twilio sender in `TWILIO_SMS_FROM` (E.164, e.g. `+1...` or a number Twilio has enabled for SMS).
4. For WhatsApp testing, open Messaging > Try it out > Send a WhatsApp message, join the Sandbox from your recipient phone using the displayed join code, and use the WhatsApp-enabled sender shown by Twilio.
5. In the Sandbox/Trial, send only Twilio-provided approved templates and only to joined/verified recipients. Trial limits may restrict SMS custom bodies and WhatsApp ContentVariables.
6. For production WhatsApp, register a WhatsApp sender and create/submit an approved utility template through Twilio Content Template Builder. Copy its Content SID (starts `HX`).
7. Never commit `backend/.env`; the repository contains only `.env.example`.

## Backend environment

Copy `backend/.env.example` to `backend/.env` and fill your values:

```env
TWILIO_ACCOUNT_SID=AC...
TWILIO_AUTH_TOKEN=...
TWILIO_API_KEY=SK...                 # optional
TWILIO_API_SECRET=...                # optional; used with API Key if both set
TWILIO_SMS_FROM=+1...
TWILIO_WHATSAPP_FROM=whatsapp:+1...
TWILIO_WHATSAPP_CONTENT_SID=HX...
TWILIO_WHATSAPP_USE_VARIABLES=false  # keep false for Trial/Sandbox
PHARMA360_BRANCH_WHATSAPP_ENABLED=false
PHARMA360_ADMIN_ALERT_PHONE=+91...
```

Twilio API Key and Secret are optional. If both are configured, the service authenticates with the API Key/Secret; otherwise it uses Account SID/Auth Token.

**Sandbox recipient requirements:** Customer and branch WhatsApp numbers must each join the Sandbox. Trial account may require verifying recipients. Branch WhatsApp is disabled by default to avoid sending to a number that has not consented/joined.

## Configure customer preferences

Customers can use the Notification Preferences page or check SMS/WhatsApp consent at checkout. `order_updates` must be enabled. Phone numbers should be E.164 (example `+9198...`).

## Enable branch WhatsApp

After the branch phone is opted in and connected/eligible, set:

```env
PHARMA360_BRANCH_WHATSAPP_ENABLED=true
```

Branch dashboard in-app notification is always created for active branch users, independent of Twilio configuration.

## Run

Backend:

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --port 8000
```

Frontend:

```powershell
cd frontend
npm install
npm run dev
```

## Test checklist

- Customer checks SMS opt-in and places an order: customer notification record exists; SMS delivery status is recorded.
- Customer checks WhatsApp opt-in, joined Sandbox, and places a new order: WhatsApp request is logged with provider status.
- Branch assigned to order receives an in-app notification; other branches do not.
- Branch SMS is attempted only if that assigned branch has a phone.
- A Twilio error does not cancel/roll back the order.
- Branch order list refreshes and shows the pending order; accept/reject/status update remains available.
- Customer order status update creates an in-app notice and opted-in external notification.

## Notes / production hardening

This implementation attempts provider calls synchronously after the order commit, with a 10-second timeout, so notification errors cannot roll back the order but may delay the checkout response. For production traffic, move sending to a durable background queue (Celery/RQ/Redis or a database-backed worker), add retry/backoff, and configure Twilio status callbacks to track `delivered`, `read`, and `failed` accurately. Current `queued` means Twilio accepted the message, not that the handset received it.
