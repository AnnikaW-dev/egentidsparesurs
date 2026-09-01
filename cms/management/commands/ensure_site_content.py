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


def _env_flag(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in ("1", "true", "yes", "on")


class Command(BaseCommand):
    help = (
        "Fill a new database (seed + snapshot). Later restarts keep admin edits. "
        "Set APPLY_CONTENT_SNAPSHOT=true only to overwrite from git."
    )

    def handle(self, *args, **options):
        """Admin text on Render lives in Postgres and must survive web restarts.

        Snapshot from git is applied only on a fresh site (missing pages) or when
        APPLY_CONTENT_SNAPSHOT=true. SEED_ON_DEPLOY still fills gaps without --force.
        """
        missing_keys = self._missing_page_keys()
        media_missing = self._media_missing()
        want_seed = _env_flag("SEED_ON_DEPLOY")
        want_snapshot = _env_flag("APPLY_CONTENT_SNAPSHOT")
        # First boot: empty site needs the committed snapshot once.
        apply_snapshot = bool(missing_keys or want_snapshot)
        should_seed = bool(missing_keys or media_missing or want_seed)

        try:
            if should_seed:
                if missing_keys:
                    reason = f"missing pages: {', '.join(missing_keys)}"
                elif media_missing:
                    reason = "missing media"
                else:
                    reason = "SEED_ON_DEPLOY (safe fill-only seed)"
                self.stdout.write(f"Seeding site content ({reason})...")
                call_command("seed_site")
            else:
                self.stdout.write("Site content and media present — skip seed.")

            if apply_snapshot:
                if want_snapshot and not missing_keys:
                    self.stdout.write(
                        "APPLY_CONTENT_SNAPSHOT=true — overwriting CMS from git snapshot."
                    )
                else:
                    self.stdout.write("Fresh site — applying cms/content_snapshot once.")
                call_command("apply_site_snapshot")
            else:
                self.stdout.write(
                    "Keeping existing CMS (admin edits). "
                    "Set APPLY_CONTENT_SNAPSHOT=true to replace from git."
                )
        except Exception as exc:
            self.stderr.write(self.style.ERROR(f"site content failed: {exc}"))
            traceback.print_exc()
            raise CommandError(f"site content failed: {exc}") from exc

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
