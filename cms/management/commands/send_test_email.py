# cms/management/commands/send_test_email.py — send one test message via configured SMTP

"""Send a test email (Render Shell: python manage.py send_test_email you@example.com)."""

from django.conf import settings
from django.core.mail import send_mail
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Send a test email using the configured SMTP/backend."

    def add_arguments(self, parser):
        parser.add_argument(
            "recipient",
            nargs="?",
            default="",
            help="Recipient address (defaults to DEFAULT_FROM_EMAIL).",
        )

    def handle(self, *args, **options):
        if not getattr(settings, "EMAIL_IS_CONFIGURED", False) and not settings.DEBUG:
            raise CommandError(
                "SMTP is not configured. Set SENDGRID_API_KEY or EMAIL_* on Render first."
            )

        recipient = (options["recipient"] or settings.DEFAULT_FROM_EMAIL).strip()
        if not recipient:
            raise CommandError("Provide a recipient or set DEFAULT_FROM_EMAIL.")

        send_mail(
            subject=f"Testmejl från {settings.DEFAULT_FROM_EMAIL}",
            message=(
                "Detta är ett testmejl från EGentid Spa-webbplatsen.\n"
                "Om du ser detta fungerar utgående e-post på Render."
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[recipient],
            fail_silently=False,
        )
        self.stdout.write(self.style.SUCCESS(f"Test email sent to {recipient}"))
