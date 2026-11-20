# PHARMA360 WhatsApp automatic order trigger

## Why it was not triggered
The notification service reads Twilio settings through `os.getenv()`. Pydantic settings reads the `.env` file for app settings, but that does not automatically populate `os.environ`. This patch explicitly loads `backend/.env` from the service file location, including when Uvicorn is started from another directory.

## Configuration
In `backend/.env`, set:

```env
TWILIO_ACCOUNT_SID=AC...
TWILIO_AUTH_TOKEN=your_rotated_token
TWILIO_WHATSAPP_FROM=whatsapp:+17372212163
TWILIO_WHATSAPP_CONTENT_SID=HX...
TWILIO_WHATSAPP_USE_VARIABLES=false
PHARMA360_BRANCH_WHATSAPP_ENABLED=false
```

The Content SID selects the approved/custom WhatsApp template in Twilio. Template content is managed by Twilio, not by the backend message body. For trial/Sandbox, keep ContentVariables disabled unless Twilio confirms your template supports variables on your account.

## Trigger behavior
When checkout includes `whatsapp_opt_in=true`, the order endpoint enables the customer's WhatsApp preference, persists the order, and invokes the notification service. It sends only if customer order updates and WhatsApp preferences are enabled and a phone number exists. Twilio acceptance is logged and recorded as `queued`/provider status; this is not a delivery guarantee.

## Debug
Backend console logs include `triggering customer WhatsApp`, `customer WhatsApp result=queued`, or a reason it was skipped.
