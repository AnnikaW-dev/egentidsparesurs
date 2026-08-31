"""Tests for CMS helpers, including accessibility alt-text fallbacks."""

import os
from unittest.mock import patch

from django.test import RequestFactory, TestCase

from cms.a11y import plain_cms_text, resolve_image_alt
from cms.models import GalleryImage, SiteSettings
from cms.seo import public_base_url


class A11yAltTextTests(TestCase):
    def test_plain_cms_text_strips_bold_markup(self):
        self.assertEqual(plain_cms_text("**Värmande** behandling"), "Värmande behandling")

    def test_resolve_image_alt_prefers_caption(self):
        alt = resolve_image_alt(
            caption="Paraffinbad för händer",
            title="Paraffin",
            fallback="Sida",
        )
        self.assertEqual(alt, "Paraffinbad för händer")

    def test_resolve_image_alt_falls_back_to_title_then_default(self):
        self.assertEqual(resolve_image_alt(title="Salongen"), "Salongen")
        self.assertEqual(resolve_image_alt(), "Bild från salongen och behandlingarna")

    def test_gallery_image_alt_text(self):
        image = GalleryImage.objects.create(title="Fotbad", caption="", sort_order=0)
        self.assertEqual(image.alt_text(), "Fotbad")
        self.assertFalse(image.missing_alt_warning())

        bare = GalleryImage.objects.create(title="", caption="", sort_order=1)
        self.assertTrue(bare.missing_alt_warning())


class PublicBaseUrlTests(TestCase):
    """Canonical URL for JSON-LD: CMS field, then env, then request host."""

    def setUp(self):
        self.site = SiteSettings.load()
        self.request = RequestFactory().get("/")

    def test_uses_cms_public_site_url(self):
        self.site.public_site_url = "https://egentid.example"
        self.site.save()
        self.assertEqual(public_base_url(self.request, self.site), "https://egentid.example")

    def test_falls_back_to_env(self):
        self.site.public_site_url = ""
        self.site.save()
        env = {"PUBLIC_SITE_URL": "https://from-env.example"}
        with patch.dict(os.environ, env, clear=False):
            os.environ.pop("RENDER_EXTERNAL_URL", None)
            self.assertEqual(
                public_base_url(self.request, self.site),
                "https://from-env.example",
            )
