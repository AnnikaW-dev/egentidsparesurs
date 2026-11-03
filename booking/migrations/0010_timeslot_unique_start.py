# One TimeSlot per start time — drop leftover 60-min luckor that share a clock.

from django.db import migrations, models


def dedupe_same_start(apps, schema_editor):
    """Remove extra luckor at the same start before unique(start) is applied.

    Uses the historical models so later columns (added_by_staff) are not required.
    """
    from collections import defaultdict

    TimeSlot = apps.get_model("booking", "TimeSlot")
    Booking = apps.get_model("booking", "Booking")
    grouped = defaultdict(list)
    for slot in TimeSlot.objects.all().order_by("pk"):
        grouped[slot.start].append(slot)
    for rows in grouped.values():
        if len(rows) < 2:
            continue
        booked_ids = set(
            Booking.objects.filter(slot__in=rows).values_list("slot_id", flat=True)
        )
        keep = next(
            (slot for slot in rows if slot.pk in booked_ids or slot.held_by_id),
            rows[0],
        )
        for slot in rows:
            if slot.pk == keep.pk or slot.pk in booked_ids or slot.held_by_id:
                continue
            slot.delete()


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
