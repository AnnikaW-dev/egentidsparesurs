"""Tests for the public contact form."""

from unittest.mock import patch

from django.core import mail
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from cms.models import PageHeroSlide, SitePage, SiteSettings
from pages.antispam import issue_guard_token, js_proof_for
from pages.models import ContactMessage

_PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
    b"\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89"
    b"\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01"
    b"\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
)


def _png(name):
    return SimpleUploadedFile(name, _PNG, content_type="image/png")


def _antispam_fields():
    """Fresh timing token and the JS checksum the contact form expects."""
    token = issue_guard_token()
    return {"form_guard": token, "form_js": js_proof_for(token)}


@override_settings(FORM_GUARD_MIN_SECONDS=0)
class ContactFormTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = Client()

    def test_contact_page_renders(self):
        response = self.client.get(reverse("contact"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Skicka meddelande")
        self.assertContains(response, "integritetspolicyn")
        self.assertContains(response, "data-form-guard")
        self.assertContains(response, "hp-field")
        self.assertNotContains(response, "challenges.cloudflare.com")

    def test_contact_form_saves_message(self):
        response = self.client.post(
            reverse("contact"),
            {
                "name": "Anna Test",
                "email": "anna@example.com",
                "phone": "0701234567",
                "subject": "Fråga",
                "message": "Hej, jag undrar över fotvård.",
                **_antispam_fields(),
            },
        )
        self.assertRedirects(response, reverse("contact"))
        self.assertEqual(ContactMessage.objects.count(), 1)
        msg = ContactMessage.objects.get()
        self.assertEqual(msg.name, "Anna Test")
        self.assertEqual(msg.status, ContactMessage.Status.NEW)

    def test_contact_rejects_invalid_email(self):
        response = self.client.post(
            reverse("contact"),
            {
                "name": "Anna Test",
                "email": "inte-en-epost",
                "message": "Hej",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(ContactMessage.objects.count(), 0)
        self.assertContains(response, "giltig e-postadress")

    def test_contact_rejects_non_digit_phone(self):
        response = self.client.post(
            reverse("contact"),
            {
                "name": "Anna Test",
                "email": "anna@example.com",
                "phone": "070-abc",
                "message": "Hej",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(ContactMessage.objects.count(), 0)
        self.assertContains(response, "bara innehålla siffror")

    def test_contact_rejects_missing_js_proof(self):
        response = self.client.post(
            reverse("contact"),
            {
                "name": "Anna Test",
                "email": "anna@example.com",
                "message": "Hej, jag undrar över fotvård.",
                "form_guard": issue_guard_token(),
                "form_js": "",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(ContactMessage.objects.count(), 0)
        self.assertContains(response, "Meddelandet kunde inte skickas.")

    def test_contact_rejects_honeypot(self):
        response = self.client.post(
            reverse("contact"),
            {
                "name": "Anna Test",
                "email": "anna@example.com",
                "message": "Hej, jag undrar över fotvård.",
                "website": "https://spam.example",
                **_antispam_fields(),
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(ContactMessage.objects.count(), 0)
        self.assertContains(response, "Meddelandet kunde inte skickas.")

    def test_contact_token_cannot_be_reused(self):
        payload = {
            "name": "Anna Test",
            "email": "anna@example.com",
            "message": "Hej, jag undrar över fotvård.",
            **_antispam_fields(),
        }
        first = self.client.post(reverse("contact"), payload)
        self.assertRedirects(first, reverse("contact"))
        second = self.client.post(
            reverse("contact"),
            {**payload, "email": "annan@example.com"},
        )
        self.assertEqual(second.status_code, 200)
        self.assertEqual(ContactMessage.objects.count(), 1)

    def test_same_name_blocked_across_messages(self):
        for i in range(4):
            response = self.client.post(
                reverse("contact"),
                {
                    "name": "RobertGlure",
                    "email": f"bot{i}@example.com",
                    "message": f"Kort {i}",
                    **_antispam_fields(),
                },
            )
            self.assertRedirects(response, reverse("contact"))
        blocked = self.client.post(
            reverse("contact"),
            {
                "name": "RobertGlure",
                "email": "bot4@example.com",
                "message": "Kort 4",
                **_antispam_fields(),
            },
        )
        self.assertEqual(blocked.status_code, 200)
        self.assertEqual(ContactMessage.objects.count(), 4)
        self.assertContains(blocked, "Meddelandet kunde inte skickas.")

    @override_settings(
        TURNSTILE_SITE_KEY="site-key-test",
        TURNSTILE_SECRET_KEY="secret-key-test",
    )
    def test_turnstile_widget_rendered_when_configured(self):
        response = self.client.get(reverse("contact"))
        self.assertContains(response, "challenges.cloudflare.com/turnstile")
        self.assertContains(response, "site-key-test")
        self.assertNotContains(response, "secret-key-test")

    @override_settings(
        TURNSTILE_SITE_KEY="site-key-test",
        TURNSTILE_SECRET_KEY="secret-key-test",
    )
    @patch("pages.forms.verify_turnstile", return_value=False)
    def test_turnstile_rejects_bad_token(self, _verify):
        response = self.client.post(
            reverse("contact"),
            {
                "name": "Anna Test",
                "email": "anna@example.com",
                "message": "Hej, jag undrar över fotvård.",
                "cf-turnstile-response": "bad-token",
                **_antispam_fields(),
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(ContactMessage.objects.count(), 0)
        self.assertContains(response, "Meddelandet kunde inte skickas.")

    @override_settings(
        TURNSTILE_SITE_KEY="site-key-test",
        TURNSTILE_SECRET_KEY="secret-key-test",
    )
    @patch("pages.forms.verify_turnstile", return_value=True)
    def test_turnstile_accepts_valid_token(self, verify):
        response = self.client.post(
            reverse("contact"),
            {
                "name": "Anna Test",
                "email": "anna@example.com",
                "message": "Hej, jag undrar över fotvård.",
                "cf-turnstile-response": "ok-token",
                **_antispam_fields(),
            },
        )
        self.assertRedirects(response, reverse("contact"))
        self.assertEqual(ContactMessage.objects.count(), 1)
        verify.assert_called_once()
        self.assertEqual(verify.call_args.args[0], "ok-token")


class AccessibilityPageTests(TestCase):
    """Public accessibility statement (EAA / WCAG 2.1 AA)."""

    def test_accessibility_page_renders(self):
        response = Client().get(reverse("accessibility"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Tillgänglighetsredogörelse")
        self.assertContains(response, "WCAG")
        self.assertContains(response, "För dig som redigerar innehåll")
        self.assertContains(response, "Galleribilder")
        self.assertContains(response, "bildspel")
        self.assertContains(response, "Cloudflare Turnstile")


class PrivacyPageTests(TestCase):
    """Public integritetspolicy (GDPR) for contact and booking data."""

    def test_privacy_page_renders(self):
        response = Client().get(reverse("privacy"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Integritetspolicy")
        self.assertContains(response, "Personuppgiftsansvarig")
        self.assertContains(response, "IMY")
        self.assertContains(response, "Cookies")
        self.assertContains(response, "statistik, reklam eller spårning")
        self.assertContains(response, "Cloudflare Turnstile")


class FooterContactTests(TestCase):
    """Production footer shows phone after seed/default SiteSettings."""

    def test_footer_shows_phone(self):
        SiteSettings.load()
        response = Client().get(reverse("home"))
        self.assertContains(response, "Mail:")
        self.assertContains(response, "egentidspaservice@gmail.com")
        self.assertContains(response, "Tel:")
        self.assertContains(response, "072-3170120")
        self.assertContains(response, "href=\"tel:0723170120\"")
        self.assertContains(response, "Integritet")


class HomeTabTitleTests(TestCase):
    """Browser tab hover text uses the current brand, not Spa & Resurs."""

    def test_home_title_rewrites_legacy_brand(self):
        SitePage.objects.filter(key=SitePage.PageKey.HOME).delete()
        SitePage.objects.create(
            key=SitePage.PageKey.HOME,
            title="En stund som bara är din!",
            meta_title="EGentid Spa & Resurs – fotvård och handvård",
            is_published=True,
        )
        settings = SiteSettings.load()
        settings.site_name = "EGentid Spa & Service"
        settings.save(update_fields=["site_name"])
        response = Client().get(reverse("home"))
        self.assertContains(
            response,
            "<title>EGentid Spa &amp; Service – fotvård och handvård</title>",
            html=False,
        )
        self.assertNotContains(response, "Resurs")


class HeroCarouselPageTests(TestCase):
    """Hem and Behandlingar: controls only when admin adds a second hero image."""

    def _page(self, key, title, hero_name):
        return SitePage.objects.create(
            key=key,
            title=title,
            is_published=True,
            hero_image=_png(hero_name),
        )

    def test_home_one_image_has_no_carousel_controls(self):
        self._page(SitePage.PageKey.HOME, "Hem", "home-hero.png")
        response = Client().get(reverse("home"))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "data-hero-carousel")
        self.assertNotContains(response, "Föregående bild")

    def test_home_two_images_shows_carousel(self):
        page = self._page(SitePage.PageKey.HOME, "Hem", "home-hero.png")
        PageHeroSlide.objects.create(page=page, image=_png("home-slide.png"), sort_order=1)
        response = Client().get(reverse("home"))
        self.assertContains(response, "data-hero-carousel")
        self.assertContains(response, "Föregående bild")
        self.assertContains(response, "Pausa bildspel")
        self.assertContains(response, "hero-carousel.js")

    def test_treatments_two_images_shows_carousel(self):
        page = self._page(SitePage.PageKey.TREATMENTS, "Behandlingar", "treat-hero.png")
        PageHeroSlide.objects.create(page=page, image=_png("treat-slide.png"), sort_order=1)
        response = Client().get(reverse("treatments"))
        self.assertContains(response, "data-hero-carousel")
        self.assertContains(response, "Nästa bild")


@override_settings(CONTACT_INBOX="egentidspaservice@gmail.com", FORM_GUARD_MIN_SECONDS=0)
class ContactNotificationEmailTests(TestCase):
    def setUp(self):
        cache.clear()
        SiteSettings.load()

    def test_contact_form_notifies_inbox(self):
        response = Client().post(
            reverse("contact"),
            {
                "name": "Anna Test",
                "email": "anna@example.com",
                "phone": "0701234567",
                "subject": "Fråga",
                "message": "Hej!",
                **_antispam_fields(),
            },
        )
        self.assertRedirects(response, reverse("contact"))
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["egentidspaservice@gmail.com"])
        self.assertEqual(mail.outbox[0].reply_to, ["anna@example.com"])
        self.assertIn("Anna Test", mail.outbox[0].body)

    def test_legacy_info_inbox_is_rewritten_to_gmail(self):
        """Old CONTACT_INBOX=info@ still delivers to the Gmail staff inbox."""
        settings = SiteSettings.load()
        settings.email = "info@egentidspaservice.se"
        settings.save(update_fields=["email"])
        with override_settings(CONTACT_INBOX="info@egentidspaservice.se"):
            from pages.emails import contact_inbox

            self.assertEqual(contact_inbox(), "egentidspaservice@gmail.com")


class PublicSeoTests(TestCase):
    """Canonical host, one Om URL, crawl files, and private noindex."""

    def test_salongen_redirects_to_om(self):
        response = self.client.get("/salongen/")
        self.assertRedirects(response, "/om/", status_code=301)

    def test_contact_head_is_indexable_local_business(self):
        response = self.client.get("/kontakt/")
        self.assertContains(
            response,
            '<link rel="canonical" href="http://testserver/kontakt/">',
            html=False,
        )
        self.assertContains(response, 'hreflang="sv"')
        self.assertContains(response, "BeautySalon")
        self.assertContains(response, "Linköping")
        self.assertContains(response, 'aria-label="Brödsmulor"')
        self.assertContains(response, 'href="/galleri/"')
        self.assertContains(response, "max-image-preview:large")

    def test_www_sitemap_and_robots_use_apex(self):
        response = self.client.get(
            "/sitemap.xml",
            HTTP_HOST="www.egentidspaservice.se",
        )
        self.assertContains(response, "https://egentidspaservice.se/om/")
        self.assertContains(response, "https://egentidspaservice.se/galleri/")
        self.assertNotContains(response, "salongen")
        self.assertNotContains(response, "www.egentidspaservice.se")
        robots = self.client.get(
            "/robots.txt",
            HTTP_HOST="www.egentidspaservice.se",
        )
        self.assertContains(
            robots,
            "Sitemap: https://egentidspaservice.se/sitemap.xml",
        )

    def test_sitemap_lists_gallery_images_and_lastmod(self):
        from django.utils import timezone

        from cms.models import GalleryImage

        page = SitePage.objects.create(
            key=SitePage.PageKey.GALLERY,
            title="Galleri",
            is_published=True,
        )
        GalleryImage.objects.create(
            title="Fotbad",
            caption="Fotbad i salongen",
            image=_png("foot-bath.png"),
            is_visible=True,
        )
        response = self.client.get("/sitemap.xml")
        self.assertContains(response, "<image:loc>")
        self.assertContains(response, "foot-bath")
        self.assertContains(response, "Fotbad i salongen")
        stamp = timezone.localtime(page.updated_at).date().isoformat()
        self.assertContains(response, f"<lastmod>{stamp}</lastmod>")

    def test_private_paths_send_noindex_header(self):
        response = self.client.get("/dashboard/")
        self.assertEqual(response["X-Robots-Tag"], "noindex, nofollow")
