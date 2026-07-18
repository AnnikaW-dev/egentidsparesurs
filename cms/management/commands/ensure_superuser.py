"""Create a superuser from env vars when none exists (for hosts without a shell)."""

import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = (
        "Create a Django superuser from DJANGO_SUPERUSER_* env vars if missing. "
        "Safe to run on every deploy."
    )

    def handle(self, *args, **options):
        """
        Adjust: set these on Render (Environment):
          DJANGO_SUPERUSER_USERNAME
          DJANGO_SUPERUSER_EMAIL
          DJANGO_SUPERUSER_PASSWORD
        """
        username = os.environ.get("DJANGO_SUPERUSER_USERNAME", "").strip()
        email = os.environ.get("DJANGO_SUPERUSER_EMAIL", "").strip()
        password = os.environ.get("DJANGO_SUPERUSER_PASSWORD", "").strip()

        if not username or not password:
            self.stdout.write(
                self.style.WARNING(
                    "Skipping superuser: set DJANGO_SUPERUSER_USERNAME and "
                    "DJANGO_SUPERUSER_PASSWORD in the host environment."
                )
            )
            return

        User = get_user_model()
        if User.objects.filter(username=username).exists():
            self.stdout.write(f"Superuser '{username}' already exists — OK.")
            return

        User.objects.create_superuser(
            username=username,
            email=email or f"{username}@example.com",
            password=password,
        )
        self.stdout.write(self.style.SUCCESS(f"Created superuser '{username}'."))
