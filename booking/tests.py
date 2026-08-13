"""Unit tests for slot generation, booking confirmation email, and SMS."""

from datetime import date, time, timedelta

from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from booking.models import Booking, ClosedDate, Service, TimeSlot, WeeklyAvailability, generate_slots_for_range
from booking.sms import outbox as sms_outbox
from booking.sms import to_e164


class GenerateSlotsTests(TestCase):
    def setUp(self):
        WeeklyAvailability.objects.create(
            weekday=0,  # Monday
            start_time=time(9, 0),
            end_time=time(11, 0),
            slot_minutes=60,
            is_active=True,
        )

    def test_generate_slots_for_range_creates_monday_slots(self):
        start = date(2026, 7, 20)  # Monday
        created = generate_slots_for_range(start, start)
        self.assertEqual(created, 2)
        self.assertEqual(TimeSlot.objects.count(), 2)

    def test_generate_slots_for_range_skips_closed_dates(self):
        start = date(2026, 7, 20)
        ClosedDate.objects.create(date=start, reason="Semester")
        created = generate_slots_for_range(start, start)
        self.assertEqual(created, 0)

    def test_generate_slots_for_range_is_idempotent(self):
        start = date(2026, 7, 20)
        first = generate_slots_for_range(start, start)
        second = generate_slots_for_range(start, start)
        self.assertEqual(first, 2)
        self.assertEqual(second, 0)
        self.assertEqual(TimeSlot.objects.count(), 2)

    def test_time_slot_is_open_false_when_past(self):
        past = timezone.now() - timedelta(hours=2)
        slot = TimeSlot.objects.create(start=past, end=past + timedelta(hours=1))
        self.assertFalse(slot.is_open)

    def test_footer_opening_hours_groups_weekdays(self):
        from booking.models import footer_opening_hours

        rows = footer_opening_hours()
        self.assertEqual(rows, [{"label": "Måndag", "hours": "09:00–11:00"}])
        WeeklyAvailability.objects.create(
            weekday=1,
            start_time=time(9, 0),
            end_time=time(11, 0),
            slot_minutes=60,
            is_active=True,
        )
        rows = footer_opening_hours()
        self.assertEqual(rows, [{"label": "Måndag–tisdag", "hours": "09:00–11:00"}])


@override_settings(SMS_BACKEND="locmem")
class BookingConfirmationNotifyTests(TestCase):
    def setUp(self):
        sms_outbox.clear()
        self.service = Service.objects.create(
            name="Testbehandling",
            slug="testbehandling",
            duration_minutes=60,
            price_sek=425,
            is_active=True,
        )
        start = timezone.now() + timedelta(days=2)
        end = start + timedelta(hours=1)
        self.slot = TimeSlot.objects.create(start=start, end=end)

    def _post(self, confirm_via=("email", "sms"), extra=None):
        data = {
            "service": self.service.slug,
            "slot": self.slot.pk,
            "customer_name": "Anna Test",
            "customer_email": "anna@example.com",
            "customer_phone": "0701234567",
            "confirm_via": list(confirm_via),
        }
        if extra:
            data.update(extra)
        return self.client.post(reverse("booking"), data)

    def test_booking_sends_email_and_sms_when_both_chosen(self):
        response = self._post(("email", "sms"))
        self.assertEqual(Booking.objects.count(), 1)
        booking = Booking.objects.get()
        self.assertTrue(booking.notify_email)
        self.assertTrue(booking.notify_sms)
        self.assertRedirects(response, reverse("booking_success", kwargs={"pk": booking.pk}))
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["anna@example.com"])
        self.assertEqual(len(sms_outbox), 1)
        self.assertEqual(sms_outbox[0]["to"], "+46701234567")
        self.assertIn("Testbehandling", sms_outbox[0]["body"])

    def test_email_only_skips_sms(self):
        self._post(("email",))
        booking = Booking.objects.get()
        self.assertTrue(booking.notify_email)
        self.assertFalse(booking.notify_sms)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(len(sms_outbox), 0)

    def test_sms_only_skips_email(self):
        self._post(("sms",))
        booking = Booking.objects.get()
        self.assertFalse(booking.notify_email)
        self.assertTrue(booking.notify_sms)
        self.assertEqual(len(mail.outbox), 0)
        self.assertEqual(len(sms_outbox), 1)

    def test_requires_at_least_one_channel(self):
        response = self.client.post(
            reverse("booking"),
            {
                "service": self.service.slug,
                "slot": self.slot.pk,
                "customer_name": "Anna Test",
                "customer_email": "anna@example.com",
                "customer_phone": "0701234567",
            },
        )
        self.assertEqual(Booking.objects.count(), 0)
        self.assertContains(response, "Välj e-post, SMS eller båda.")

    def test_success_page_mentions_email_and_sms(self):
        self._post(("email", "sms"))
        booking = Booking.objects.get()
        response = self.client.get(reverse("booking_success", kwargs={"pk": booking.pk}))
        self.assertContains(response, "En bekräftelse har skickats till")
        self.assertContains(response, "anna@example.com")
        self.assertContains(response, "Ett bekräftelse-SMS har skickats till")
        self.assertContains(response, "0701234567")

    def test_to_e164_converts_swedish_mobile(self):
        self.assertEqual(to_e164("0701234567"), "+46701234567")
        self.assertEqual(to_e164("46701234567"), "+46701234567")
