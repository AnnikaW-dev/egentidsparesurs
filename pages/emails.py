"""Notify site owner when a contact form message is submitted."""

import logging

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string

from cms.models import SiteSettings

logger = logging.getLogger(__name__)


def contact_inbox() -> str:
    """Recipient for contact notifications — env override, else CMS site email."""
    override = getattr(settings, "CONTACT_INBOX", "") or ""
    if override.strip():
        return override.strip()
    return (SiteSettings.load().email or "").strip()


def send_contact_notification(message) -> bool:
    """Email staff about a new ContactMessage. Returns True when sent."""
    to_email = contact_inbox()
    if not to_email:
        logger.warning("Contact notification skipped: no CONTACT_INBOX or site email.")
        return False

    site = SiteSettings.load()
    context = {"message": message, "site": site}
    subject = render_to_string(
        "pages/emails/contact_notification_subject.txt",
        context,
    ).strip()
    body = render_to_string("pages/emails/contact_notification_body.txt", context)

    mail = EmailMultiAlternatives(
        subject=subject,
        body=body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[to_email],
        reply_to=[message.email],
    )
    try:
        mail.send(fail_silently=False)
        return True
    except Exception as exc:
        logger.exception(
            "Failed to send contact notification for message %s to %s: %s",
            message.pk,
            to_email,
            exc,
        )
        return False
