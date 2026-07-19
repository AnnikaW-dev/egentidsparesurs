"""Tests for the public contact form."""

from django.test import Client, TestCase
from django.urls import reverse

from pages.models import ContactMessage


class ContactFormTests(TestCase):
    def setUp(self):
        self.client = Client()

    def test_contact_page_renders(self):
        response = self.client.get(reverse("contact"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Skicka meddelande")

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
