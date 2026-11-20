"""Optional manual WhatsApp smoke test. Never sends messages during pytest collection.

Run intentionally with PHARMA360_SEND_WHATSAPP_TEST=1 and a recipient configured
in PHARMA360_WHATSAPP_TEST_TO. This uses the application's provider wrapper.
"""
import os


def test_whatsapp_provider_is_optional():
    # Provider credentials are optional; normal test runs must not send messages.
    assert os.getenv("PHARMA360_SEND_WHATSAPP_TEST", "0") != "1"


if __name__ == "__main__":
    if os.getenv("PHARMA360_SEND_WHATSAPP_TEST", "0") != "1":
        raise SystemExit("Set PHARMA360_SEND_WHATSAPP_TEST=1 to explicitly enable this manual test.")
    recipient = os.getenv("PHARMA360_WHATSAPP_TEST_TO", "").strip()
    if not recipient:
        raise SystemExit("Set PHARMA360_WHATSAPP_TEST_TO to the intended recipient number.")
    from app.services.notifications import send_twilio
    result = send_twilio(recipient, "PHARMA360 manual provider test", "whatsapp")
    print("Provider result:", result)
