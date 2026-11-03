# Rebuild bookable slots for the 6-month Boka/admin window.

from django.db import migrations


def sync_six_month_horizon(apps, schema_editor):
    """Backfill already ran in production.

    Do not call the live sync here. Later migrations add columns that the
    current sync function reads, so a fresh migrate would fail on this step.
    Saving Veckoschema still rebuilds luckor.
    """
    return None


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("booking", "0008_booking_notify_sms_default_false"),
    ]

    operations = [
        migrations.RunPython(sync_six_month_horizon, noop),
    ]
