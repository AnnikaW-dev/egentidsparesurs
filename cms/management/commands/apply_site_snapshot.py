# cms/management/commands/apply_site_snapshot.py — load git CMS onto this database

"""Apply cms/content_snapshot. Used on first boot, not on every Render restart."""

from django.core.management.base import BaseCommand

from cms.snapshot import apply_snapshot


class Command(BaseCommand):
    help = (
        "Copy snapshot pages/gallery/images into the current database and MEDIA_ROOT. "
        "Overwrites CMS text. Does not change public_site_url. "
        "Boot only runs this on a fresh site or APPLY_CONTENT_SNAPSHOT=true."
    )

    def handle(self, *args, **options):
        applied = apply_snapshot(stdout=self.stdout)
        if applied:
            self.stdout.write(self.style.SUCCESS("Content snapshot applied."))
        else:
            self.stdout.write("No snapshot to apply.")
