"""Send booking confirmation emails to customers and a copy to staff."""

import logging

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils import timezone

from cms.models import SiteSettings
from pages.emails import contact_inbox

logger = logging.getLogger(__name__)


def _booking_context(booking):
    """Shared template context for customer and staff booking mail."""
    site = SiteSettings.load()
    slot_local = timezone.localtime(booking.slot.start)
    return {
        "booking": booking,
        "site": site,
        "slot_local": slot_local,
    }


def send_booking_confirmation(booking) -> bool:
    """Email the customer a confirmation for a saved booking.

    Uses SiteSettings for sender/reply-to branding. Returns True when sent.
    """
    context = _booking_context(booking)
    site = context["site"]
    subject = render_to_string("booking/emails/confirmation_subject.txt", context).strip()
    text_body = render_to_string("booking/emails/confirmation_body.txt", context)
    html_body = render_to_string("booking/emails/confirmation_body.html", context)

    message = EmailMultiAlternatives(
        subject=subject,
        body=text_body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[booking.customer_email],
        reply_to=[site.email] if site.email else None,
    )
    message.attach_alternative(html_body, "text/html")
    try:
        message.send(fail_silently=False)
        return True
    except Exception as exc:
        logger.exception(
            "Failed to send booking confirmation for booking %s to %s: %s",
            booking.pk,
            booking.customer_email,
            exc,
        )
        return False


def send_booking_staff_notification(booking) -> bool:
    """Email staff when a customer books. Returns True when sent.

    Always sent when a booking is saved. Inbox is contact_inbox().
    """
    to_email = contact_inbox()
    if not to_email:
        logger.warning("Staff booking notice skipped: no CONTACT_INBOX or site email.")
        return False

    context = _booking_context(booking)
    subject = render_to_string(
        "booking/emails/staff_notification_subject.txt",
        context,
    ).strip()
    body = render_to_string("booking/emails/staff_notification_body.txt", context)

    message = EmailMultiAlternatives(
        subject=subject,
        body=body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[to_email],
        reply_to=[booking.customer_email] if booking.customer_email else None,
    )
    try:
        message.send(fail_silently=False)
        return True
    except Exception as exc:
        logger.exception(
            "Failed to send staff booking notice for booking %s to %s: %s",
            booking.pk,
            to_email,
            exc,
        )
        return False
