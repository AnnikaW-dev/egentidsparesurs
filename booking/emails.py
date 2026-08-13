"""Send booking confirmation emails to customers."""

import logging

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils import timezone

from cms.models import SiteSettings

logger = logging.getLogger(__name__)


def send_booking_confirmation(booking) -> bool:
    """Email the customer a confirmation for a saved booking.

    Uses SiteSettings for sender/reply-to branding. Returns True when sent.
    """
    site = SiteSettings.load()
    slot_local = timezone.localtime(booking.slot.start)
    context = {
        "booking": booking,
        "site": site,
        "slot_local": slot_local,
    }
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
    except Exception:
        logger.exception(
            "Failed to send booking confirmation for booking %s to %s",
            booking.pk,
            booking.customer_email,
        )
        return False
