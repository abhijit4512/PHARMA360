# PHARMA360 Notifications

## Included flows
- Customer in-app notification on order placement and order status changes.
- Branch staff and super-admin in-app alert for new orders.
- Customer SMS when SMS is enabled in their preferences and they opted in at checkout.
- Customer WhatsApp when WhatsApp is enabled in preferences and opted in at checkout.
- Branch/admin SMS alerts when provider and recipient values are configured.
- Optional admin WhatsApp alert when WhatsApp sender and approved Content SID are configured.

## Twilio configuration
Set the values in `backend/.env`:
- `TWILIO_ACCOUNT_SID`
- `TWILIO_AUTH_TOKEN`
- `TWILIO_SMS_FROM`
- `TWILIO_WHATSAPP_FROM` (format `whatsapp:+...`)
- `TWILIO_WHATSAPP_CONTENT_SID` (the approved template Content SID)
- `PHARMA360_ADMIN_ALERT_PHONE` (E.164, e.g. `+91...`)

The WhatsApp sender uses `ContentSid` rather than free-form `Body`, which is appropriate for Sandbox/template messaging. Trial accounts may only message verified/joined Sandbox participants and permitted templates. Template variables are not sent by this implementation. If your approved template requires variables, configure a no-variable template for this test flow or upgrade/configure a production WhatsApp sender and then implement its variable mapping.

Never share or commit `.env`; it contains API credentials.
