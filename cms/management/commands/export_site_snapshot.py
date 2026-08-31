# cms/management/commands/export_site_snapshot.py — save local CMS into git

"""Write cms/content_snapshot from this machine's admin content + media."""

from django.core.management.base import BaseCommand

from cms.snapshot import export_snapshot


class Command(BaseCommand):
    help = (
        "Export pages, gallery, and images from this database into "
        "cms/content_snapshot/. Push the folder so Render can apply it."
    )

    def handle(self, *args, **options):
        root = export_snapshot(stdout=self.stdout)
        self.stdout.write(self.style.SUCCESS(f"Snapshot ready: {root}"))
