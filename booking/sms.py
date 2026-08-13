"""Send booking confirmation SMS. Console locally; Twilio or 46elks in production."""

import json
import logging
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from django.conf import settings
from django.template.loader import render_to_string
from django.utils import timezone

from cms.models import SiteSettings

logger = logging.getLogger(__name__)

# Test helper — messages collected when SMS_BACKEND=locmem.
outbox: list[dict] = []


def to_e164(phone: str) -> str:
    """Turn stored digits into E.164, assuming Sweden when the number starts with 0."""
    digits = "".join(ch for ch in str(phone or "") if ch.isdigit())
    if not digits:
        return ""
    if digits.startswith("00"):
        return f"+{digits[2:]}"
    if digits.startswith("46"):
        return f"+{digits}"
    if digits.startswith("0"):
        return f"+46{digits[1:]}"
    return f"+{digits}"


def send_sms(to_e164_number: str, body: str) -> bool:
    """Send one SMS. Returns True when the backend accepts it."""
    backend = getattr(settings, "SMS_BACKEND", "console")
    if backend == "auto":
        backend = _auto_backend()
    if backend == "locmem":
        outbox.append({"to": to_e164_number, "body": body})
        return True
    if backend == "console":
        print(f"SMS to {to_e164_number}: {body}")
        return True
    if backend == "twilio":
        return _send_twilio(to_e164_number, body)
    if backend == "46elks":
        return _send_46elks(to_e164_number, body)
    logger.error("Unknown SMS_BACKEND %s", backend)
    return False


def send_booking_confirmation_sms(booking) -> bool:
    """SMS the customer a short confirmation for a saved booking."""
    site = SiteSettings.load()
    slot_local = timezone.localtime(booking.slot.start)
    body = render_to_string(
        "booking/sms/confirmation.txt",
        {"booking": booking, "site": site, "slot_local": slot_local},
    ).strip()
    number = to_e164(booking.customer_phone)
    if not number:
        logger.error("Booking %s has no sendable phone number", booking.pk)
        return False
    try:
        return send_sms(number, body)
    except Exception:
        logger.exception(
            "Failed to send booking SMS for booking %s to %s",
            booking.pk,
            number,
        )
        return False


def _auto_backend() -> str:
    """Pick Twilio or 46elks from env, otherwise console (no live send)."""
    if settings.TWILIO_ACCOUNT_SID and settings.TWILIO_AUTH_TOKEN:
        return "twilio"
    if settings.ELKS_USERNAME and settings.ELKS_PASSWORD:
        return "46elks"
    return "console"


def _send_twilio(to_number: str, body: str) -> bool:
    sid = settings.TWILIO_ACCOUNT_SID
    token = settings.TWILIO_AUTH_TOKEN
    from_number = settings.TWILIO_FROM_NUMBER
    if not sid or not token or not from_number:
        logger.error("Twilio SMS is missing TWILIO_ACCOUNT_SID, AUTH_TOKEN, or FROM_NUMBER")
        return False
    url = f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json"
    data = urlencode({"From": from_number, "To": to_number, "Body": body}).encode()
    request = Request(url, data=data, method="POST")
    _add_basic_auth(request, sid, token)
    return _post(request, "Twilio")


def _send_46elks(to_number: str, body: str) -> bool:
    username = settings.ELKS_USERNAME
    password = settings.ELKS_PASSWORD
    from_label = settings.ELKS_FROM
    if not username or not password or not from_label:
        logger.error("46elks SMS is missing ELKS_USERNAME, PASSWORD, or FROM")
        return False
    data = urlencode({"from": from_label, "to": to_number, "message": body}).encode()
    request = Request("https://api.46elks.com/a1/sms", data=data, method="POST")
    _add_basic_auth(request, username, password)
    return _post(request, "46elks")


def _add_basic_auth(request: Request, username: str, password: str) -> None:
    import base64

    token = base64.b64encode(f"{username}:{password}".encode()).decode()
    request.add_header("Authorization", f"Basic {token}")


def _post(request: Request, provider: str) -> bool:
    timeout = int(getattr(settings, "SMS_TIMEOUT", 20))
    try:
        with urlopen(request, timeout=timeout) as response:
            status = response.status
            payload = response.read()
    except HTTPError as exc:
        logger.error("%s SMS failed: HTTP %s %s", provider, exc.code, exc.read())
        return False
    except URLError:
        logger.exception("%s SMS request failed", provider)
        return False
    if status >= 400:
        logger.error("%s SMS failed: HTTP %s %s", provider, status, payload)
        return False
    try:
        json.loads(payload.decode() or "{}")
    except json.JSONDecodeError:
        pass
    return True
