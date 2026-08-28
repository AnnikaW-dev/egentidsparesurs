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
            return

        msg = (
            "Email is NOT configured for production. Booking confirmations and contact "
            "notifications will not reach real inboxes.\n"
            "Set on Render → Environment:\n"
            "  SENDGRID_API_KEY=<key>  (recommended; also verify DEFAULT_FROM_EMAIL in SendGrid)\n"
            "  — or —\n"
            "  EMAIL_HOST, EMAIL_PORT, EMAIL_HOST_USER, EMAIL_HOST_PASSWORD, EMAIL_USE_TLS\n"
            "  DEFAULT_FROM_EMAIL=info@egentidspaservice.se\n"
            "Optional: CONTACT_INBOX=info@egentidspaservice.se (defaults to CMS site email)\n"
            f"Current backend: {backend}"
        )
        if options["strict"] and not settings.DEBUG:
            self.stderr.write(self.style.ERROR(msg))
            raise SystemExit(1)
        self.stderr.write(self.style.WARNING(msg))
