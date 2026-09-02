# Confirmation is e-post only; keep notify_sms on the row but default off.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("booking", "0007_timeslot_held_by"),
    ]

    operations = [
        migrations.AlterField(
            model_name="booking",
            name="notify_sms",
            field=models.BooleanField(default=False),
        ),
    ]
