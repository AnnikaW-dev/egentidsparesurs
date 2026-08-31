"""Tests for the public contact form."""

from django.core import mail
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from cms.models import SiteSettings
from pages.models import ContactMessage


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


class PrivacyPageTests(TestCase):
    """Public integritetspolicy (GDPR) for contact and booking data."""

    def test_privacy_page_renders(self):
        response = Client().get(reverse("privacy"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Integritetspolicy")
        self.assertContains(response, "Personuppgiftsansvarig")
        self.assertContains(response, "IMY")


class FooterContactTests(TestCase):
    """Production footer shows phone after seed/default SiteSettings."""

    def test_footer_shows_phone(self):
        SiteSettings.load()
        response = Client().get(reverse("home"))
        self.assertContains(response, "Tel:")
        self.assertContains(response, "072-3170120")
        self.assertContains(response, "href=\"tel:0723170120\"")
        self.assertContains(response, "Integritet")


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
