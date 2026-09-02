# cms/management/commands/check_email_config.py — verify SMTP before relying on mail on Render

"""Warn or fail when production has no working email configuration."""

from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Check that email/SMTP is configured for production (booking + contact)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--strict",
            action="store_true",
            help="Exit with code 1 when email is not configured (for CI/deploy hooks).",
        )

    def handle(self, *args, **options):
        configured = getattr(settings, "EMAIL_IS_CONFIGURED", False)
        backend = settings.EMAIL_BACKEND

        if configured:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Email OK: {backend} via {settings.EMAIL_HOST}:{settings.EMAIL_PORT} "
                    f"(from {settings.DEFAULT_FROM_EMAIL})"
                )
            )
            inbox = (getattr(settings, "CONTACT_INBOX", "") or "").strip()
            host = (settings.EMAIL_HOST or "").lower()
            user = (settings.EMAIL_HOST_USER or "").strip()
            if host in ("smtp.gmail.com", "smtp.googlemail.com") and inbox and user:
                if inbox.lower() != user.lower() and f"<{user.lower()}>" not in inbox.lower():
                    self.stderr.write(
                        self.style.WARNING(
                            f"CONTACT_INBOX is {inbox} while Gmail sends as {user}. "
                            "Set CONTACT_INBOX to that Gmail or contact form mail may bounce."
                        )
                    )
            return

        msg = (
            "Email is NOT configured for production. Booking confirmations and contact "
            "notifications will not reach real inboxes.\n"
            "Set on Render → Environment:\n"
            "  SENDGRID_API_KEY=<key>  (recommended; also verify DEFAULT_FROM_EMAIL in SendGrid)\n"
            "  — or —\n"
            "  EMAIL_HOST, EMAIL_PORT, EMAIL_HOST_USER, EMAIL_HOST_PASSWORD, EMAIL_USE_TLS\n"
            "  DEFAULT_FROM_EMAIL=egentidspaservice@gmail.com\n"
            "Optional: CONTACT_INBOX=egentidspaservice@gmail.com (defaults to CMS site email)\n"
            f"Current backend: {backend}"
        )
        if options["strict"] and not settings.DEBUG:
            self.stderr.write(self.style.ERROR(msg))
            raise SystemExit(1)
        self.stderr.write(self.style.WARNING(msg))
