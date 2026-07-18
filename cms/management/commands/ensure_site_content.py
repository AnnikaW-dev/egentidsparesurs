"""Ensure CMS pages and media files exist on deploy."""

import os
from pathlib import Path

from django.core.management import call_command
from django.core.management.base import BaseCommand

from cms.models import SitePage, SiteSettings


class Command(BaseCommand):
    help = "Seed when pages or media files are missing, or when SEED_ON_DEPLOY=true."

    def handle(self, *args, **options):
        """
        Adjust: SEED_ON_DEPLOY=true forces a full seed; otherwise seeds if content/media missing.
        """
        force = os.environ.get("SEED_ON_DEPLOY", "").strip().lower() in ("1", "true", "yes", "on")
        has_home = SitePage.objects.filter(key=SitePage.PageKey.HOME, is_published=True).exists()
        media_missing = self._media_missing()

        if has_home and not media_missing and not force:
            self.stdout.write("Site content and media present — skip seed.")
            return

        reason = "forced" if force else ("missing media" if media_missing else "empty DB")
        self.stdout.write(f"Seeding site content ({reason})...")
        call_command("seed_site")
        self.stdout.write(self.style.SUCCESS("Site content ready."))

    def _media_missing(self):
        """True if logo/hero files are referenced but not on disk."""
        settings = SiteSettings.load()
        if not settings.logo or not settings.logo.name:
            return True
        try:
            if not Path(settings.logo.path).exists():
                return True
        except Exception:
            return True
        home = SitePage.objects.filter(key=SitePage.PageKey.HOME).first()
        if home and home.hero_image and home.hero_image.name:
            try:
                if not Path(home.hero_image.path).exists():
                    return True
            except Exception:
                return True
        return False
