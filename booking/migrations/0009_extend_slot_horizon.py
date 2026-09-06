# Rebuild bookable slots for the 6-month Boka/admin window.

from django.db import migrations


def sync_six_month_horizon(apps, schema_editor):
    """Create missing luckor out to PUBLIC_SLOT_HORIZON_DAYS after the constant change."""
    from booking.models import sync_future_slots

    sync_future_slots()


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("booking", "0008_booking_notify_sms_default_false"),
    ]

    operations = [
        migrations.RunPython(sync_six_month_horizon, noop),
    ]
