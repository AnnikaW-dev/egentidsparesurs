"""Tests for the public contact form."""

from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from cms.models import PageHeroSlide, SitePage, SiteSettings
from pages.models import ContactMessage

_PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
    b"\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89"
    b"\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01"
    b"\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
)


def _png(name):
    return SimpleUploadedFile(name, _PNG, content_type="image/png")


class ContactFormTests(TestCase):
    def setUp(self):
        self.client = Client()

    def test_contact_page_renders(self):
        response = self.client.get(reverse("contact"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Skicka meddelande")
        self.assertContains(response, "integritetspolicyn")

    def test_contact_form_saves_message(self):
        response = self.client.post(
            reverse("contact"),
            {
                "name": "Anna Test",
                "email": "anna@example.com",
                "phone": "0701234567",
                "subject": "Fråga",
                "message": "Hej, jag undrar över fotvård.",
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


class FooterContactTests(TestCase):
    """Production footer shows phone after seed/default SiteSettings."""

    def test_footer_shows_phone(self):
        SiteSettings.load()
        response = Client().get(reverse("home"))
        self.assertContains(response, "Mail:")
        self.assertContains(response, "info@egentidspaservice.se")
        self.assertContains(response, "Tel:")
        self.assertContains(response, "072-3170120")
        self.assertContains(response, "href=\"tel:0723170120\"")
        self.assertContains(response, "Integritet")


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
        self.assertNotContains(response, "Pausa bildspel")
        self.assertContains(response, "hero-carousel.js")

    def test_treatments_two_images_shows_carousel(self):
        page = self._page(SitePage.PageKey.TREATMENTS, "Behandlingar", "treat-hero.png")
        PageHeroSlide.objects.create(page=page, image=_png("treat-slide.png"), sort_order=1)
        response = Client().get(reverse("treatments"))
        self.assertContains(response, "data-hero-carousel")
        self.assertContains(response, "Nästa bild")


@override_settings(CONTACT_INBOX="info@egentidspaservice.se")
class ContactNotificationEmailTests(TestCase):
    def setUp(self):
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
            },
        )
        self.assertRedirects(response, reverse("contact"))
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["info@egentidspaservice.se"])
        self.assertEqual(mail.outbox[0].reply_to, ["anna@example.com"])
        self.assertIn("Anna Test", mail.outbox[0].body)
