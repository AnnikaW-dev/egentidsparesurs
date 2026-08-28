# cms/migrations/0013_brand_service_name.py — default brand rename Resurs → Service

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("cms", "0012_sitepage_cta_labels"),
    ]

    operations = [
        migrations.AlterField(
            model_name="sitesettings",
            name="site_name",
            field=models.CharField(default="EGentid Spa & Service", max_length=120),
        ),
        migrations.AlterField(
            model_name="sitesettings",
            name="default_meta_description",
            field=models.CharField(
                blank=True,
                default=(
                    "Fotvård, spa-pedikyr och värmande manikyr. "
                    "Boka egentid hos EGentid Spa & Service."
                ),
                help_text=(
                    "Standard meta description (ca 150–160 tecken) om sidan saknar egen."
                ),
                max_length=160,
            ),
        ),
    ]
