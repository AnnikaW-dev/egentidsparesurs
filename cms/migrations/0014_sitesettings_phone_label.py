# cms/migrations/0014_sitesettings_phone_label.py — admin label for footer phone

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("cms", "0013_brand_service_name"),
    ]

    operations = [
        migrations.AlterField(
            model_name="sitesettings",
            name="phone",
            field=models.CharField(
                blank=True,
                help_text="Visas i sidfoten under Kontakt. Lämna tomt för att dölja raden.",
                max_length=40,
                verbose_name="Telefonnummer",
            ),
        ),
    ]
