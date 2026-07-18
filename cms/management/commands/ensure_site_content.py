"""Ensure CMS pages exist on deploy (fixes empty-DB 404 on Render)."""

import os

from django.core.management import call_command
from django.core.management.base import BaseCommand

from cms.models import SitePage


class Command(BaseCommand):
    help = "Run seed_site when no published pages exist, or when SEED_ON_DEPLOY=true."

    def handle(self, *args, **options):
        """
        Adjust: set SEED_ON_DEPLOY=true to force re-seed; otherwise only seeds if empty.
        """
        force = os.environ.get("SEED_ON_DEPLOY", "").strip().lower() in ("1", "true", "yes", "on")
        has_home = SitePage.objects.filter(key=SitePage.PageKey.HOME, is_published=True).exists()

        if has_home and not force:
            self.stdout.write("Site content already present — skip seed.")
            return

        self.stdout.write("Seeding site content...")
        call_command("seed_site")
        self.stdout.write(self.style.SUCCESS("Site content ready."))
