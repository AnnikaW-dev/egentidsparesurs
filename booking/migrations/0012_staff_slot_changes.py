# booking/migrations/0012_staff_slot_changes.py — staff can add or remove one lucka

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("booking", "0011_booking_email_optional"),
    ]

    operations = [
        migrations.AddField(
            model_name="timeslot",
            name="added_by_staff",
            field=models.BooleanField(
                default=False,
                help_text="Behålls när veckoschemat sparas. Syns på Boka även utanför öppettiderna.",
                verbose_name="Tillagd av personal",
            ),
        ),
        migrations.CreateModel(
            name="RemovedSlot",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("start", models.DateTimeField(unique=True)),
            ],
            options={
                "verbose_name": "borttagen lucka",
                "verbose_name_plural": "borttagna luckor",
            },
        ),
    ]
