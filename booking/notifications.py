"""Send booking confirmations on the channels the customer chose."""

from .emails import send_booking_confirmation as send_booking_confirmation_email
from .sms import send_booking_confirmation_sms


def send_booking_notifications(booking) -> dict:
    """Send email and/or SMS. Values are True/False, or None if not requested."""
    results = {"email": None, "sms": None}
    if booking.notify_email:
        results["email"] = send_booking_confirmation_email(booking)
    if booking.notify_sms:
        results["sms"] = send_booking_confirmation_sms(booking)
    return results
