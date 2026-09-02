# Extra TimeSlots held by a booking that lasts longer than one calendar slot.

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("booking", "0006_weekly_lunch"),
    ]

    operations = [
        migrations.AddField(
            model_name="timeslot",
            name="held_by",
            field=models.ForeignKey(
                blank=True,
                help_text="Upptagen av en längre bokning som börjar i en tidigare lucka.",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="held_slots",
                to="booking.booking",
            ),
        ),
        migrations.AlterField(
            model_name="service",
            name="duration_minutes",
            field=models.PositiveIntegerField(
                default=60,
                help_text="Själva behandlingen. På Boka reserveras den tiden plus 30 minuter.",
                verbose_name="Behandlingstid (min)",
            ),
        ),
    ]
