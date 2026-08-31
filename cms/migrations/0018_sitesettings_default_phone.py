# cms/migrations/0018_sitesettings_default_phone.py — footer Tel: 072-3170120

from django.db import migrations, models

DEFAULT_PHONE = "072-3170120"


def set_default_phone(apps, schema_editor):
    """Fill empty phone on existing SiteSettings so production footer shows Tel:."""
    SiteSettings = apps.get_model("cms", "SiteSettings")
    for row in SiteSettings.objects.filter(phone=""):
        row.phone = DEFAULT_PHONE
        row.save(update_fields=["phone"])


class Migration(migrations.Migration):

    dependencies = [
        ("cms", "0017_contact_email_service"),
    ]

    operations = [
        migrations.AlterField(
            model_name="sitesettings",
            name="phone",
            field=models.CharField(
                blank=True,
                default="072-3170120",
                help_text="Visas i sidfoten under Kontakt. Lämna tomt för att dölja raden.",
                max_length=40,
                verbose_name="Telefonnummer",
            ),
        ),
        migrations.RunPython(set_default_phone, migrations.RunPython.noop),
    ]
