# cms/migrations/0016_gallery_caption_a11y.py — bildtext help for admin editors

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("cms", "0015_gallery_image_picks"),
    ]

    operations = [
        migrations.AlterField(
            model_name="contentblock",
            name="gallery_image",
            field=models.ForeignKey(
                blank=True,
                help_text=(
                    "Välj en bild från Galleriet. Bildtexten från Galleribilder "
                    "används som alt-text."
                ),
                null=True,
                on_delete=models.SET_NULL,
                related_name="content_blocks",
                to="cms.galleryimage",
                verbose_name="Bild från galleri",
            ),
        ),
        migrations.AlterField(
            model_name="galleryimage",
            name="caption",
            field=models.CharField(
                blank=True,
                help_text=(
                    "Kort beskrivning för skärmläsare. Används på Galleri och när bilden "
                    "väljes på sidor/block. Tom = titeln används."
                ),
                max_length=255,
                verbose_name="Bildtext (alt-text)",
            ),
        ),
        migrations.AlterField(
            model_name="sitepage",
            name="hero_gallery_image",
            field=models.ForeignKey(
                blank=True,
                help_text=(
                    "Välj en bild från Galleriet. Bildtexten från Galleribilder "
                    "används som alt-text på sidan."
                ),
                null=True,
                on_delete=models.SET_NULL,
                related_name="hero_pages",
                to="cms.galleryimage",
                verbose_name="Hero från galleri",
            ),
        ),
    ]
