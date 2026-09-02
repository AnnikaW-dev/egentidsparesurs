"""Tests for CMS helpers, including accessibility alt-text fallbacks."""

import os
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import RequestFactory, TestCase

from cms.a11y import plain_cms_text, resolve_image_alt
from cms.models import ContentBlock, GalleryImage, PageHeroSlide, SitePage, SiteSettings
from cms.seo import public_base_url

# 1×1 PNG — enough for ImageField without a real photo.
_PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
    b"\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89"
    b"\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01"
    b"\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
)


def _png(name):
    """Tiny PNG upload for hero/carousel tests."""
    return SimpleUploadedFile(name, _PNG, content_type="image/png")


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


class ContentBlockBodyTests(TestCase):
    """Admin on Windows saves CRLF; price line must still split from the rest."""

    def setUp(self):
        self.page = SitePage.objects.create(
            key=SitePage.PageKey.TREATMENTS,
            title="Behandlingar",
            is_published=True,
        )

    def test_price_meta_splits_crlf_paragraphs(self):
        block = ContentBlock.objects.create(
            page=self.page,
            title="Evig Lycka – Spa-pedikyr",
            body="425 kr · ca 60 min\r\n\r\nEn klassisk spa-pedikyr.\r\n\r\n## Passar dig som:\r\n• mjuka fötter",
            sort_order=1,
        )
        self.assertEqual(block.price_meta(), "425 kr | ca 60 min")
        types = [s["type"] for s in block.body_sections()]
        self.assertIn("para", types)
        self.assertIn("heading", types)
        self.assertIn("list", types)
        self.assertTrue(any("klassisk" in s.get("text", "") for s in block.body_sections()))


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


class HeroCarouselItemsTests(TestCase):
    """One hero stays still; extra Hero-karusell rows become a slideshow."""

    def setUp(self):
        self.page = SitePage.objects.create(
            key=SitePage.PageKey.HOME,
            title="Hem",
            is_published=True,
            hero_image=_png("hero-main.png"),
        )

    def test_single_hero_is_one_item(self):
        items = self.page.hero_carousel_items()
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["alt"], "Hem")

    def test_extra_slide_makes_two_items(self):
        PageHeroSlide.objects.create(
            page=self.page,
            image=_png("hero-extra.png"),
            sort_order=1,
        )
        items = self.page.hero_carousel_items()
        self.assertEqual(len(items), 2)

    def test_same_gallery_image_is_not_duplicated(self):
        gallery = GalleryImage.objects.create(
            title="Fotbad",
            caption="Paraffinbad",
            image=_png("shared-hero.png"),
        )
        page = SitePage.objects.create(
            key=SitePage.PageKey.TREATMENTS,
            title="Behandlingar",
            is_published=True,
            hero_gallery_image=gallery,
        )
        PageHeroSlide.objects.create(page=page, gallery_image=gallery, sort_order=1)
        items = page.hero_carousel_items()
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["alt"], "Paraffinbad")


class SiteSnapshotTests(TestCase):
    """Local CMS snapshot round-trip for Render deploy."""

    def test_export_apply_restores_page_text(self):
        import tempfile
        from pathlib import Path

        from django.core.files.uploadedfile import SimpleUploadedFile
        from django.test import override_settings
        from PIL import Image

        from cms.snapshot import apply_snapshot, export_snapshot

        tmp = Path(tempfile.mkdtemp())
        media = tmp / "media"
        snap = tmp / "snap"
        media.mkdir()

        buf = __import__("io").BytesIO()
        Image.new("RGB", (80, 80), (180, 120, 80)).save(buf, "JPEG", quality=85)
        jpeg = SimpleUploadedFile("hero.jpg", buf.getvalue(), content_type="image/jpeg")

        with override_settings(MEDIA_ROOT=str(media)):
            SitePage.objects.filter(key=SitePage.PageKey.HOME).delete()
            SitePage.objects.create(
                key=SitePage.PageKey.HOME,
                title="Lokal hero-titel",
                subtitle="Lokal underrubrik",
                body="Lokal brödtext från admin.",
                is_published=True,
                hero_image=jpeg,
            )
            export_snapshot(dest=snap)
            SitePage.objects.filter(key=SitePage.PageKey.HOME).update(
                title="Annan titel",
                body="",
            )
            apply_snapshot(src=snap)
            page = SitePage.objects.get(key=SitePage.PageKey.HOME)
            self.assertEqual(page.title, "Lokal hero-titel")
            self.assertEqual(page.body, "Lokal brödtext från admin.")
            self.assertTrue(page.hero_image)
            self.assertTrue(Path(page.hero_image.path).is_file())


class SitePageAdminGalleryPickTests(TestCase):
    """Hero and carousel gallery picks must be a visible dropdown, not autocomplete search."""

    def test_home_admin_lists_gallery_images_in_select(self):
        from django.contrib.auth import get_user_model
        from django.test import Client
        from django.urls import reverse

        get_user_model().objects.create_superuser("admin", "admin@example.com", "secret")
        page = SitePage.objects.create(
            key=SitePage.PageKey.HOME,
            title="Hem",
            is_published=True,
        )
        GalleryImage.objects.create(
            title="Fotbad i salongen",
            caption="Fotbad",
            image=_png("admin-gallery.jpg"),
        )
        client = Client()
        self.assertTrue(client.login(username="admin", password="secret"))
        response = client.get(reverse("admin:cms_sitepage_change", args=[page.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Fotbad i salongen")
        self.assertContains(response, "välj från galleri")
        self.assertContains(response, "hero_slides-0-gallery_image")
        self.assertNotContains(response, "admin/autocomplete/")


class EnsureSiteContentTests(TestCase):
    """Render restarts must not wipe admin CMS; snapshot only on fresh DB or env flag."""

    def setUp(self):
        from cms.management.commands.ensure_site_content import REQUIRED_PAGE_KEYS

        for key in REQUIRED_PAGE_KEYS:
            SitePage.objects.create(key=key, title=key, is_published=True)

    @patch("cms.management.commands.ensure_site_content.ensure_snapshot_media", return_value=0)
    @patch("cms.management.commands.ensure_site_content.call_command")
    @patch(
        "cms.management.commands.ensure_site_content.Command._media_missing",
        return_value=False,
    )
    def test_restart_does_not_reapply_snapshot(self, _media, mock_call, _copy_media):
        with patch.dict(
            os.environ, {"SEED_ON_DEPLOY": "", "APPLY_CONTENT_SNAPSHOT": ""}, clear=False
        ):
            from django.core.management import call_command as run

            run("ensure_site_content")
        self.assertEqual(mock_call.call_args_list, [])

    @patch("cms.management.commands.ensure_site_content.ensure_snapshot_media", return_value=0)
    @patch("cms.management.commands.ensure_site_content.call_command")
    @patch(
        "cms.management.commands.ensure_site_content.Command._media_missing",
        return_value=False,
    )
    def test_env_flag_reapplies_snapshot(self, _media, mock_call, _copy_media):
        with patch.dict(os.environ, {"APPLY_CONTENT_SNAPSHOT": "true"}, clear=False):
            from django.core.management import call_command as run

            run("ensure_site_content")
        names = [c.args[0] for c in mock_call.call_args_list]
        self.assertEqual(names, ["apply_site_snapshot"])


class BrandTitleTests(TestCase):
    """Tab titles must use Spa & Service, not leftover Spa & Resurs."""

    def test_document_title_rewrites_resurs_and_skips_duplicate_name(self):
        from cms.brand import document_title

        title = document_title(
            "EGentid Spa & Resurs – fotvård och handvård",
            "EGentid Spa & Service",
        )
        self.assertEqual(title, "EGentid Spa & Service – fotvård och handvård")
        self.assertNotIn("Resurs", title)

    def test_replace_legacy_brand_updates_page_meta_title(self):
        from cms.brand import replace_legacy_brand_in_db

        SitePage.objects.filter(key=SitePage.PageKey.HOME).delete()
        page = SitePage.objects.create(
            key=SitePage.PageKey.HOME,
            title="Hem",
            meta_title="EGentid Spa & Resurs – fotvård och handvård",
            is_published=True,
        )
        changed = replace_legacy_brand_in_db()
        page.refresh_from_db()
        self.assertGreaterEqual(changed, 1)
        self.assertEqual(page.meta_title, "EGentid Spa & Service – fotvård och handvård")


class SnapshotMediaRestoreTests(TestCase):
    """Postgres can keep image paths after the Render disk is empty — recopy files only."""

    def test_ensure_snapshot_media_copies_missing_file(self):
        import tempfile
        from pathlib import Path

        from django.test import override_settings

        from cms.snapshot import MIN_MEDIA_BYTES, ensure_snapshot_media

        tmp = Path(tempfile.mkdtemp())
        files = tmp / "files" / "gallery"
        files.mkdir(parents=True)
        (files / "fotmassage.jpg").write_bytes(b"x" * (MIN_MEDIA_BYTES + 50))
        media = tmp / "media"
        media.mkdir()
        with override_settings(MEDIA_ROOT=str(media)):
            copied = ensure_snapshot_media(src=tmp)
            copied_again = ensure_snapshot_media(src=tmp)
        dest = media / "gallery" / "fotmassage.jpg"
        self.assertGreaterEqual(copied, 1)
        self.assertEqual(copied_again, 0)
        self.assertTrue(dest.is_file())
