# booking/migrations/0011_booking_email_optional.py — phone bookings may omit e-post

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("booking", "0010_timeslot_unique_start"),
    ]

    operations = [
        migrations.AlterField(
            model_name="booking",
            name="customer_email",
            field=models.EmailField(
                blank=True,
                help_text="Kan lämnas tom när kunden bokas via telefon.",
                max_length=254,
            ),
        ),
    ]
