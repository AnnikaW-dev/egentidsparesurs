"""Send customer booking confirmations plus a staff copy to the contact inbox."""

from .emails import send_booking_confirmation as send_booking_confirmation_email
from .emails import send_booking_staff_notification


def send_booking_notifications(booking) -> dict:
    """Send customer e-post plus a staff copy. Values are True/False, or None if skipped."""
    results = {
        "email": None,
        "staff": send_booking_staff_notification(booking),
    }
    if booking.notify_email:
        results["email"] = send_booking_confirmation_email(booking)
    return results
