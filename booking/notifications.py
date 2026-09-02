"""Send customer booking confirmations plus a staff copy to the contact inbox."""

from .emails import send_booking_confirmation as send_booking_confirmation_email
from .emails import send_booking_staff_notification
from .sms import send_booking_confirmation_sms


def send_booking_notifications(booking) -> dict:
    """Send customer email/SMS plus a staff copy. Values are True/False, or None if skipped."""
    results = {
        "email": None,
        "sms": None,
        "staff": send_booking_staff_notification(booking),
    }
    if booking.notify_email:
        results["email"] = send_booking_confirmation_email(booking)
    if booking.notify_sms:
        results["sms"] = send_booking_confirmation_sms(booking)
    return results
