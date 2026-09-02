# Lunch break per weekday on WeeklyAvailability — skipped on public Boka.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("booking", "0005_merge_20260813_1705"),
    ]

    operations = [
        migrations.AddField(
            model_name="weeklyavailability",
            name="lunch_start",
            field=models.TimeField(
                blank=True,
                help_text="Lämna tomt om du inte tar lunch den dagen.",
                null=True,
                verbose_name="Lunch från",
            ),
        ),
        migrations.AddField(
            model_name="weeklyavailability",
            name="lunch_end",
            field=models.TimeField(
                blank=True,
                help_text="Luckor under lunchen går inte att boka på Boka.",
                null=True,
                verbose_name="Lunch till",
            ),
        ),
    ]
