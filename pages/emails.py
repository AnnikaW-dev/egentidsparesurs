"""Notify site owner when a contact form message is submitted."""

import logging

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string

from cms.brand import CONTACT_EMAIL, is_legacy_contact_email
from cms.models import SiteSettings

logger = logging.getLogger(__name__)


def contact_inbox() -> str:
    """Staff inbox for contact form and new-booking notices.

    CONTACT_INBOX wins when it is a current address. Old info@ values (env or CMS)
    are rewritten to CONTACT_EMAIL so leftover Render settings still reach Gmail.
    """
    override = (getattr(settings, "CONTACT_INBOX", "") or "").strip()
    if override and not is_legacy_contact_email(override):
        return override
    site_email = (SiteSettings.load().email or "").strip()
    if site_email and not is_legacy_contact_email(site_email):
        return site_email
    return CONTACT_EMAIL


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
