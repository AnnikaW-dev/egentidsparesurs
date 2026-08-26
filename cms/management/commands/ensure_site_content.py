"""Ensure CMS pages and media files exist on deploy."""

import os
import traceback
from pathlib import Path

from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError

from cms.models import SitePage, SiteSettings

# Adjust: pages that must exist for nav/URLs to work (no setup_needed screen).
REQUIRED_PAGE_KEYS = (
    SitePage.PageKey.HOME,
    SitePage.PageKey.SALON,
    SitePage.PageKey.TREATMENTS,
    SitePage.PageKey.WARMING,
    SitePage.PageKey.SEASONS,
    SitePage.PageKey.BOOKING,
    SitePage.PageKey.CONTACT,
    SitePage.PageKey.SERVICE,
)


class Command(BaseCommand):
    help = (
        "Seed missing pages/media when needed. Never overwrites admin CMS text "
        "(seed_site preserves edits unless run with --force)."
    )

    def handle(self, *args, **options):
        """
        Adjust: SEED_ON_DEPLOY=true runs a safe seed (fills gaps only).
        Admin edits are kept. To reset content intentionally:
        python manage.py seed_site --force
        """
        want_seed = os.environ.get("SEED_ON_DEPLOY", "").strip().lower() in (
            "1",
            "true",
            "yes",
            "on",
        )
        missing_keys = self._missing_page_keys()
        media_missing = self._media_missing()

        if not missing_keys and not media_missing and not want_seed:
            self.stdout.write("Site content and media present — skip seed.")
            return

        if missing_keys:
            reason = f"missing pages: {', '.join(missing_keys)}"
        elif media_missing:
            reason = "missing media"
        else:
            reason = "SEED_ON_DEPLOY (safe fill-only seed)"

        self.stdout.write(f"Seeding site content ({reason})...")
        try:
            # Never pass --force here — deploy must not wipe admin edits.
            call_command("seed_site")
        except Exception as exc:
            self.stderr.write(self.style.ERROR(f"seed_site failed: {exc}"))
            traceback.print_exc()
            raise CommandError(f"seed_site failed: {exc}") from exc

        still_missing = self._missing_page_keys()
        if still_missing:
            raise CommandError(
                f"After seed, pages still missing: {', '.join(still_missing)}"
            )
        self.stdout.write(self.style.SUCCESS("Site content ready."))

    def _missing_page_keys(self):
        """Return list of required page keys that are not published yet."""
        existing = set(
            SitePage.objects.filter(
                key__in=REQUIRED_PAGE_KEYS,
                is_published=True,
            ).values_list("key", flat=True)
        )
        return [key for key in REQUIRED_PAGE_KEYS if key not in existing]

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
