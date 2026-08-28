# cms/migrations/0017_contact_email_service.py — info@ → egentidspaservice.se

from django.db import migrations, models

OLD_EMAIL = "info@egentidsparesurs.se"
NEW_EMAIL = "info@egentidspaservice.se"


def update_contact_email(apps, schema_editor):
    SiteSettings = apps.get_model("cms", "SiteSettings")
    SiteSettings.objects.filter(email=OLD_EMAIL).update(email=NEW_EMAIL)


class Migration(migrations.Migration):

    dependencies = [
        ("cms", "0016_gallery_caption_a11y"),
    ]

    operations = [
        migrations.AlterField(
            model_name="sitesettings",
            name="email",
            field=models.EmailField(
                blank=True,
                default="info@egentidspaservice.se",
                max_length=254,
            ),
        ),
        migrations.RunPython(update_contact_email, migrations.RunPython.noop),
    ]
