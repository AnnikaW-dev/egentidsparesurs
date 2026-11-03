"""Tests for CMS helpers, including accessibility alt-text fallbacks."""

import os
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import RequestFactory, TestCase

from cms.a11y import plain_cms_text, resolve_image_alt
from cms.models import ContentBlock, GalleryImage, PageHeroSlide, SitePage, SiteSettings
from cms.seo import (
    DEFAULT_META_DESCRIPTION,
    DEFAULT_META_DESCRIPTION_PREVIOUS,
    TREATMENTS_META_DESCRIPTION,
    canonical_url,
    local_business_json_ld,
    postal_address,
    public_base_url,
    upgrade_stock_seo,
)

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
    """Canonical URL: CMS field, then PUBLIC_SITE_URL, then the public domain."""

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

    def test_render_hostname_is_not_canonical(self):
        self.site.public_site_url = "https://egentid.onrender.com"
        self.site.save()
        request = RequestFactory().get("/", HTTP_HOST="egentid.onrender.com")
        with patch.dict(os.environ, {"PUBLIC_SITE_URL": ""}, clear=False):
            os.environ.pop("PUBLIC_SITE_URL", None)
            self.assertEqual(
                public_base_url(request, self.site),
                "https://egentidspaservice.se",
            )
            self.assertEqual(
                canonical_url(request, self.site, "/om/"),
                "https://egentidspaservice.se/om/",
            )

    def test_www_request_uses_apex(self):
        self.site.public_site_url = ""
        self.site.save()
        request = RequestFactory().get("/", HTTP_HOST="www.egentidspaservice.se")
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("PUBLIC_SITE_URL", None)
            self.assertEqual(
                public_base_url(request, self.site),
                "https://egentidspaservice.se",
            )


class LocalBusinessSchemaTests(TestCase):
    """JSON-LD uses the city from the public copy and real bookable data."""

    def setUp(self):
        self.site = SiteSettings.load()
        self.site.public_site_url = "https://egentidspaservice.se"
        self.site.address = "Egen ingång en trappa ner"
        self.site.phone = "072-3170120"
        self.site.save()
        self.request = RequestFactory().get("/", HTTP_HOST="egentidspaservice.se")

    def test_stock_snippets_fit_and_name_the_city(self):
        self.assertLessEqual(len(DEFAULT_META_DESCRIPTION), 160)
        self.assertLessEqual(len(TREATMENTS_META_DESCRIPTION), 160)
        self.assertIn("Linköping", DEFAULT_META_DESCRIPTION)
        self.assertIn(
            "Boka egentid hos EGentid Spa & Service.",
            DEFAULT_META_DESCRIPTION_PREVIOUS[0],
        )

    def test_entrance_note_is_not_a_street_address(self):
        address = postal_address("Egen ingång en trappa ner")
        self.assertEqual(address["addressLocality"], "Linköping")
        self.assertNotIn("streetAddress", address)

    def test_postal_line_becomes_street_and_city(self):
        address = postal_address("Storgatan 1, 582 20 Linköping")
        self.assertEqual(address["streetAddress"], "Storgatan 1")
        self.assertEqual(address["postalCode"], "582 20")
        self.assertEqual(address["addressLocality"], "Linköping")

    def test_json_ld_includes_hours_offer_and_phone(self):
        from datetime import time

        from booking.models import WeeklyAvailability

        WeeklyAvailability.objects.create(
            weekday=0,
            start_time=time(9, 0),
            end_time=time(16, 0),
            is_active=True,
        )
        page = SitePage.objects.create(
            key=SitePage.PageKey.TREATMENTS,
            title="Behandlingar",
            is_published=True,
        )
        ContentBlock.objects.create(
            page=page,
            title="**Spa-pedikyr**",
            body="425 kr · ca 60 min\n\nEn lugn fotvård.",
            sort_order=1,
            is_visible=True,
        )
        payload = local_business_json_ld(self.request, self.site)
        self.assertIn("BeautySalon", payload)
        self.assertIn("Linköping", payload)
        self.assertIn("+46723170120", payload)
        self.assertIn("Monday", payload)
        self.assertIn("09:00", payload)
        self.assertIn("Spa-pedikyr", payload)
        self.assertNotIn("**", payload)
        self.assertIn('"price": "425"', payload)
        self.assertNotIn("Egen ingång", payload)

    def test_upgrade_stock_seo_rewrites_only_known_sentences(self):
        self.site.default_meta_description = DEFAULT_META_DESCRIPTION_PREVIOUS[0]
        self.site.public_site_url = "https://egentid.onrender.com"
        self.site.save()
        SitePage.objects.create(
            key=SitePage.PageKey.TREATMENTS,
            title="Behandlingar",
            meta_description=TREATMENTS_META_DESCRIPTION,
            is_published=True,
        )
        # Custom treatments text must survive; the constant above is already current.
        custom = SitePage.objects.get(key=SitePage.PageKey.TREATMENTS)
        custom.meta_description = "Egen text om priser."
        custom.save(update_fields=["meta_description"])
        self.assertGreaterEqual(upgrade_stock_seo(), 1)
        self.site.refresh_from_db()
        custom.refresh_from_db()
        self.assertEqual(self.site.default_meta_description, DEFAULT_META_DESCRIPTION)
        self.assertEqual(self.site.public_site_url, "https://egentidspaservice.se")
        self.assertEqual(custom.meta_description, "Egen text om priser.")

    def test_meta_description_strips_bold_markup(self):
        page = SitePage.objects.create(
            key=SitePage.PageKey.HOME,
            title="Hem",
            body="**Fotvård** i lugn miljö.\n\nMer text.",
            is_published=True,
        )
        self.assertEqual(page.seo_description(), "Fotvård i lugn miljö.")


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
        return_value=True,
    )
    def test_missing_media_does_not_run_seed(self, _media, mock_call, _copy_media):
        """Broken photos must not rewrite CMS text via seed_site."""
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

    def test_restore_missing_uuid_gallery_file_keeps_caption(self):
        import tempfile
        from pathlib import Path

        from django.core.files.uploadedfile import SimpleUploadedFile
        from django.test import override_settings
        from PIL import Image

        from cms.snapshot import MIN_MEDIA_BYTES, restore_missing_cms_media

        tmp = Path(tempfile.mkdtemp())
        files = tmp / "files" / "gallery"
        files.mkdir(parents=True)
        (files / "pedicure-foot-file.jpg").write_bytes(b"x" * (MIN_MEDIA_BYTES + 50))
        media = tmp / "media"
        media.mkdir()
        buf = __import__("io").BytesIO()
        Image.new("RGB", (40, 40), (10, 10, 10)).save(buf, "JPEG")
        placeholder = SimpleUploadedFile(
            "placeholder.jpg", buf.getvalue(), content_type="image/jpeg"
        )
        gi = GalleryImage.objects.create(
            title="Fotvård",
            caption="En fot som får hälarna dilade",
            image=placeholder,
            sort_order=0,
        )
        uuid_rel = "gallery/e824325a-6250-41e9-84a1-4d113d288b34.jpg"
        gi.image.name = uuid_rel
        gi.save(update_fields=["image"])
        with override_settings(MEDIA_ROOT=str(media)):
            copied = restore_missing_cms_media(src=tmp)
            gi.refresh_from_db()
        dest = media / "gallery" / "e824325a-6250-41e9-84a1-4d113d288b34.jpg"
        self.assertGreaterEqual(copied, 1)
        self.assertTrue(dest.is_file())
        self.assertEqual(gi.image.name, uuid_rel)
        self.assertEqual(gi.caption, "En fot som får hälarna dilade")
