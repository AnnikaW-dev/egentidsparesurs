# One TimeSlot per start time — drop leftover 60-min luckor that share a clock.

from django.db import migrations, models


def dedupe_same_start(apps, schema_editor):
    """Remove extra luckor at the same start before unique(start) is applied."""
    from booking.models import dedupe_timeslots_with_same_start

    dedupe_timeslots_with_same_start()


class Migration(migrations.Migration):
    # Postgres cannot ALTER booking_timeslot in the same transaction as the
    # DELETE above (pending trigger events). Each operation must commit first.
    atomic = False

    dependencies = [
        ("booking", "0009_extend_slot_horizon"),
    ]

    operations = [
        migrations.RunPython(dedupe_same_start, migrations.RunPython.noop),
        migrations.AlterUniqueTogether(
            name="timeslot",
            unique_together=set(),
        ),
        migrations.AlterField(
            model_name="timeslot",
            name="start",
            field=models.DateTimeField(
                help_text="En lucka per starttid. Samma klockslag får inte finnas två gånger.",
                unique=True,
            ),
        ),
    ]
