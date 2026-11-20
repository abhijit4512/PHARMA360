"""PHARMA360 external notification providers (Twilio SMS/WhatsApp)."""
import json
import logging
import os
import httpx
import smtplib
from email.message import EmailMessage
from pathlib import Path
from dotenv import load_dotenv

# Load backend/.env even when uvicorn is launched from another working directory.
_BACKEND_ENV = Path(__file__).resolve().parents[2] / ".env"
load_dotenv(_BACKEND_ENV, override=False)

logger = logging.getLogger("pharma360.notifications")


def _credentials():
    sid = os.getenv("TWILIO_ACCOUNT_SID", "").strip()
    token = os.getenv("TWILIO_AUTH_TOKEN", "").strip()
    api_key = os.getenv("TWILIO_API_KEY", "").strip()
    api_secret = os.getenv("TWILIO_API_SECRET", "").strip()
    if api_key and api_secret and sid:
        return sid, (api_key, api_secret)
    if sid and token:
        return sid, (sid, token)
    return None, None


def send_twilio(to_phone: str, body: str, channel: str = "sms", variables: dict | None = None) -> str:
    """Returns compact status for notification log. Never raises to order flow."""
    sid, auth = _credentials()
    sender = os.getenv("TWILIO_SMS_FROM", "").strip() if channel == "sms" else os.getenv("TWILIO_WHATSAPP_FROM", "").strip()
    if not sid or not auth or not sender or not to_phone:
        missing = [name for name, value in {
            "TWILIO_ACCOUNT_SID": sid, "TWILIO_AUTH_TOKEN": auth,
            "TWILIO_WHATSAPP_FROM" if channel == "whatsapp" else "TWILIO_SMS_FROM": sender,
            "recipient": to_phone,
        }.items() if not value]
        logger.warning("Twilio %s not configured; missing: %s", channel, ", ".join(missing))
        return "not_configured"

    to_value = to_phone.strip()
    from_value = sender
    if channel == "whatsapp":
        if not to_value.startswith("whatsapp:"):
            to_value = f"whatsapp:{to_value}"
        if not from_value.startswith("whatsapp:"):
            from_value = f"whatsapp:{from_value}"
        content_sid = os.getenv("TWILIO_WHATSAPP_CONTENT_SID", "").strip()
        if not content_sid:
            logger.warning("WhatsApp skipped: TWILIO_WHATSAPP_CONTENT_SID is missing")
            return "not_configured"
        data = {"To": to_value, "From": from_value, "ContentSid": content_sid}
        # Trial/Sandbox should leave this disabled; trials only allow the documented parameters.
        if os.getenv("TWILIO_WHATSAPP_USE_VARIABLES", "false").lower() == "true" and variables:
            data["ContentVariables"] = json.dumps(variables, ensure_ascii=False)
    else:
        data = {"To": to_value, "From": from_value, "Body": body}

    try:
        response = httpx.post(
            f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json",
            data=data, auth=auth, timeout=10,
        )
        response.raise_for_status()
        result = response.json()
        # Twilio commonly returns queued initially. Store a short status, not the SID.
        status = result.get("status", "sent")
        logger.info("Twilio %s accepted message (status=%s, sid=%s)", channel, status, result.get("sid", "unknown"))
        return "queued" if status in ("queued", "accepted", "scheduled") else status
    except httpx.HTTPStatusError as exc:
        # Keep credentials and phone numbers out of logs; record the provider code only.
        try:
            provider_code = exc.response.json().get("code")
        except Exception:
            provider_code = exc.response.status_code
        logger.warning("Twilio %s delivery failed (provider code %s)", channel, provider_code)
        return "failed"
    except Exception as exc:
        logger.warning("Twilio %s delivery failed (%s)", channel, type(exc).__name__)
        return "failed"


def send_email(to_email: str, subject: str, body: str) -> str:
    """Send email through optional SMTP configuration. Returns safe status; never raises."""
    host=os.getenv("SMTP_HOST","").strip()
    port=int(os.getenv("SMTP_PORT","587") or 587)
    username=os.getenv("SMTP_USER","").strip()
    password=os.getenv("SMTP_PASSWORD","").strip()
    sender=os.getenv("SMTP_FROM",username).strip()
    if not host or not sender or not to_email:
        logger.info("SMTP not configured; customer email skipped")
        return "not_configured"
    msg=EmailMessage()
    msg["Subject"]=subject
    msg["From"]=sender
    msg["To"]=to_email
    msg.set_content(body)
    try:
        with smtplib.SMTP(host,port,timeout=12) as server:
            server.ehlo()
            if os.getenv("SMTP_USE_TLS","true").lower()=="true":
                server.starttls()
                server.ehlo()
            if username and password:
                server.login(username,password)
            server.send_message(msg)
        return "sent"
    except Exception as exc:
        logger.warning("SMTP email delivery failed (%s)",type(exc).__name__)
        return "failed"
