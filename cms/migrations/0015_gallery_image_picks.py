# cms/migrations/0015_gallery_image_picks.py — pick Galleribilder on pages and blocks

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("cms", "0014_sitesettings_phone_label"),
    ]

    operations = [
        migrations.AddField(
            model_name="contentblock",
            name="gallery_image",
            field=models.ForeignKey(
                blank=True,
                help_text="Välj en bild från Galleriet. Har företräde framför egen uppladdning.",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="content_blocks",
                to="cms.galleryimage",
                verbose_name="Bild från galleri",
            ),
        ),
        migrations.AddField(
            model_name="sitepage",
            name="hero_gallery_image",
            field=models.ForeignKey(
                blank=True,
                help_text="Välj en bild från Galleriet. Har företräde framför egen uppladdning.",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="hero_pages",
                to="cms.galleryimage",
                verbose_name="Hero från galleri",
            ),
        ),
        migrations.AlterField(
            model_name="contentblock",
            name="image",
            field=models.ImageField(
                blank=True,
                help_text="Används om ingen bild är vald från Galleriet ovan.",
                upload_to="blocks/",
                verbose_name="Egen bild",
            ),
        ),
        migrations.AlterField(
            model_name="sitepage",
            name="hero_image",
            field=models.ImageField(
                blank=True,
                help_text="Används om ingen bild är vald från Galleriet ovan.",
                upload_to="pages/",
                verbose_name="Egen hero-bild",
            ),
        ),
    ]
