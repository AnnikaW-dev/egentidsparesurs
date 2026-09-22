# visits/migrations/0001_site_traffic.py — daily totals and anonymized visitor hashes

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="SiteTrafficDay",
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
                ("day", models.DateField(unique=True, verbose_name="datum")),
                (
                    "pageviews",
                    models.PositiveIntegerField(default=0, verbose_name="sidvisningar"),
                ),
                (
                    "unique_visitors",
                    models.PositiveIntegerField(default=0, verbose_name="unika besökare"),
                ),
            ],
            options={
                "verbose_name": "besöksdag",
                "verbose_name_plural": "besöksstatistik",
                "ordering": ["-day"],
            },
        ),
        migrations.CreateModel(
            name="SiteVisitor",
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
                ("visitor_hash", models.CharField(max_length=64, unique=True)),
                ("first_seen", models.DateTimeField(auto_now_add=True)),
                ("last_seen", models.DateTimeField(auto_now=True)),
                ("last_seen_date", models.DateField()),
                ("visit_count", models.PositiveIntegerField(default=1)),
            ],
            options={
                "verbose_name": "besökare",
                "verbose_name_plural": "besökare",
            },
        ),
    ]
