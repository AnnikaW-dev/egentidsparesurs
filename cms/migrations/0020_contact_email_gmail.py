# cms/migrations/0020_contact_email_gmail.py — info@ → Gmail staff inbox

from django.db import migrations, models

# Frozen at migration time — do not import live CONTACT_EMAIL from brand.py.
NEW_EMAIL = "egentidspaservice@gmail.com"
OLD_EMAILS = (
    "info@egentidspaservice.se",
    "info@egentidsparesurs.se",
)


def update_contact_email(apps, schema_editor):
    """Move leftover info@ addresses to the Gmail staff inbox."""
    SiteSettings = apps.get_model("cms", "SiteSettings")
    SiteSettings.objects.filter(email__in=OLD_EMAILS).update(email=NEW_EMAIL)


class Migration(migrations.Migration):

    dependencies = [
        ("cms", "0019_page_hero_slide"),
    ]

    operations = [
        migrations.AlterField(
            model_name="sitesettings",
            name="email",
            field=models.EmailField(
                blank=True,
                default="egentidspaservice@gmail.com",
                help_text=(
                    "Visas i sidfoten. Kontaktformulär och nya bokningar skickas hit "
                    "om CONTACT_INBOX inte är satt i miljön."
                ),
                max_length=254,
                verbose_name="E-post",
            ),
        ),
        migrations.RunPython(update_contact_email, migrations.RunPython.noop),
    ]
