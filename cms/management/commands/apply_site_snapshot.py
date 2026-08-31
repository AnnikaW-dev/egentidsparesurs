# cms/management/commands/apply_site_snapshot.py — load git CMS onto this database

"""Apply cms/content_snapshot on deploy so Render matches the local site."""

from django.core.management.base import BaseCommand

from cms.snapshot import apply_snapshot


class Command(BaseCommand):
    help = (
        "Copy snapshot pages/gallery/images into the current database and MEDIA_ROOT. "
        "Does not overwrite public_site_url. Safe to run on every boot."
    )

    def handle(self, *args, **options):
        applied = apply_snapshot(stdout=self.stdout)
        if applied:
            self.stdout.write(self.style.SUCCESS("Content snapshot applied."))
        else:
            self.stdout.write("No snapshot to apply.")
