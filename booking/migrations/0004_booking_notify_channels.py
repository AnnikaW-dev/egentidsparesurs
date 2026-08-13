# Store whether the customer wants confirmation by email and/or SMS.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("booking", "0003_booking_email_required"),
    ]

    operations = [
        migrations.AddField(
            model_name="booking",
            name="notify_email",
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name="booking",
            name="notify_sms",
            field=models.BooleanField(default=True),
        ),
    ]
