# cms/migrations/0019_page_hero_slide.py — extra hero images for Hem / Behandlingar carousel

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("cms", "0018_sitesettings_default_phone"),
    ]

    operations = [
        migrations.CreateModel(
            name="PageHeroSlide",
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
                (
                    "image",
                    models.ImageField(
                        blank=True,
                        help_text="Används om ingen bild är vald från Galleriet.",
                        upload_to="heroes/",
                        verbose_name="Egen bild",
                    ),
                ),
                (
                    "sort_order",
                    models.PositiveIntegerField(default=0, verbose_name="Ordning"),
                ),
                (
                    "gallery_image",
                    models.ForeignKey(
                        blank=True,
                        help_text="Välj från Galleribilder. Bildtexten används som alt-text.",
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="page_hero_slides",
                        to="cms.galleryimage",
                        verbose_name="Bild från galleri",
                    ),
                ),
                (
                    "page",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="hero_slides",
                        to="cms.sitepage",
                    ),
                ),
            ],
            options={
                "verbose_name": "extra hero-bild",
                "verbose_name_plural": "hero-karusell (fler än en bild = bildspel)",
                "ordering": ["sort_order", "id"],
            },
        ),
    ]
