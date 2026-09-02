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


class SyncSlotsFromWeeklyTests(TestCase):
    """Saving Veckoschema must add/remove public Boka slots, but keep bookings."""

    def setUp(self):
        self.monday = timezone.localdate()
        while self.monday.weekday() != 0:
            self.monday += timedelta(days=1)
        self.rule = WeeklyAvailability.objects.create(
            weekday=0,
            start_time=time(9, 0),
            end_time=time(12, 0),
            slot_minutes=60,
            is_active=True,
        )

    def test_sync_creates_slots_matching_hours(self):
        from booking.models import sync_slots_for_range

        created, deleted = sync_slots_for_range(self.monday, self.monday)
        self.assertEqual(created, 3)
        self.assertEqual(deleted, 0)
        self.assertEqual(TimeSlot.objects.count(), 3)

    def test_shorter_hours_remove_unbooked_slots(self):
        from booking.models import sync_slots_for_range

        sync_slots_for_range(self.monday, self.monday)
        self.rule.end_time = time(10, 0)
        self.rule.save()
        created, deleted = sync_slots_for_range(self.monday, self.monday)
        self.assertEqual(created, 0)
        self.assertEqual(deleted, 2)
        self.assertEqual(TimeSlot.objects.count(), 1)

    def test_booked_slot_is_kept_when_hours_shrink(self):
        from booking.models import sync_slots_for_range

        sync_slots_for_range(self.monday, self.monday)
        late = TimeSlot.objects.order_by("-start").first()
        service = Service.objects.create(
            name="Test",
            slug="test",
            duration_minutes=60,
            is_active=True,
        )
        Booking.objects.create(
            slot=late,
            service=service,
            customer_name="Anna",
            customer_email="anna@example.com",
            customer_phone="0701234567",
        )
        self.rule.end_time = time(10, 0)
        self.rule.save()
        sync_slots_for_range(self.monday, self.monday)
        late.refresh_from_db()
        self.assertTrue(Booking.objects.filter(pk=late.booking.pk).exists())
        self.assertEqual(TimeSlot.objects.count(), 2)

    def test_admin_save_updates_public_boka_slots(self):
        from django.contrib.auth import get_user_model

        get_user_model().objects.create_superuser("emma", "emma@example.com", "secret")
        self.client.login(username="emma", password="secret")
        url = reverse("admin:booking_weeklyavailability_change", args=[self.rule.pk])
        response = self.client.post(
            url,
            {
                "weekday": "0",
                "start_time": "10:00:00",
                "end_time": "12:00:00",
                "slot_minutes": "60",
                "is_active": "on",
                "lunch_start": "",
                "lunch_end": "",
            },
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Bokningsbara tider på Boka är uppdaterade")
        starts = [
            timezone.localtime(slot.start).time()
            for slot in TimeSlot.objects.order_by("start")
            if timezone.localtime(slot.start).date() == self.monday
        ]
        self.assertEqual(starts, [time(10, 0), time(11, 0)])

    def test_lunch_window_is_not_bookable(self):
        from booking.models import generate_slots_for_range, sync_slots_for_range

        self.rule.end_time = time(16, 0)
        self.rule.lunch_start = time(12, 0)
        self.rule.lunch_end = time(13, 0)
        self.rule.save()
        created, deleted = sync_slots_for_range(self.monday, self.monday)
        self.assertEqual(created, 6)
        starts = [
            timezone.localtime(slot.start).strftime("%H:%M")
            for slot in TimeSlot.objects.order_by("start")
        ]
        self.assertEqual(starts, ["09:00", "10:00", "11:00", "13:00", "14:00", "15:00"])
        self.assertNotIn("12:00", starts)
        self.assertEqual(generate_slots_for_range(self.monday, self.monday), 0)

    def test_footer_shows_lunch_gap(self):
        from booking.models import footer_opening_hours

        self.rule.end_time = time(16, 0)
        self.rule.lunch_start = time(12, 0)
        self.rule.lunch_end = time(13, 0)
        self.rule.save()
        rows = footer_opening_hours()
        self.assertEqual(
            rows,
            [{"label": "Måndag", "hours": "09:00–12:00, 13:00–16:00"}],
        )


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
        TimeSlot.objects.create(start=end, end=end + timedelta(hours=1))

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
        self.assertEqual(len(mail.outbox), 2)
        recipients = {tuple(m.to) for m in mail.outbox}
        self.assertEqual(
            recipients,
            {("anna@example.com",), ("egentidspaservice@gmail.com",)},
        )
        self.assertEqual(len(sms_outbox), 1)
        self.assertEqual(sms_outbox[0]["to"], "+46701234567")
        self.assertIn("Testbehandling", sms_outbox[0]["body"])

    def test_email_only_skips_sms(self):
        self._post(("email",))
        booking = Booking.objects.get()
        self.assertTrue(booking.notify_email)
        self.assertFalse(booking.notify_sms)
        self.assertEqual(len(mail.outbox), 2)
        recipients = {tuple(m.to) for m in mail.outbox}
        self.assertEqual(
            recipients,
            {("anna@example.com",), ("egentidspaservice@gmail.com",)},
        )
        self.assertEqual(len(sms_outbox), 0)

    def test_sms_only_skips_email(self):
        self._post(("sms",))
        booking = Booking.objects.get()
        self.assertFalse(booking.notify_email)
        self.assertTrue(booking.notify_sms)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["egentidspaservice@gmail.com"])
        self.assertIn("Ny bokning", mail.outbox[0].subject)
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


@override_settings(SMS_BACKEND="locmem")
class BookingDurationBufferTests(TestCase):
    """A booking reserves treatment length plus 30 minutes of calendar slots."""

    def setUp(self):
        sms_outbox.clear()
        self.service = Service.objects.create(
            name="Spa",
            slug="spa",
            duration_minutes=60,
            is_active=True,
        )
        start = timezone.now() + timedelta(days=3)
        self.slot_a = TimeSlot.objects.create(
            start=start, end=start + timedelta(hours=1)
        )
        self.slot_b = TimeSlot.objects.create(
            start=start + timedelta(hours=1),
            end=start + timedelta(hours=2),
        )
        self.slot_c = TimeSlot.objects.create(
            start=start + timedelta(hours=2),
            end=start + timedelta(hours=3),
        )

    def test_sixty_minute_treatment_holds_the_next_slot(self):
        response = self.client.post(
            reverse("booking"),
            {
                "service": self.service.slug,
                "slot": self.slot_a.pk,
                "customer_name": "Anna",
                "customer_email": "anna@example.com",
                "customer_phone": "0701234567",
                "confirm_via": ["email"],
            },
        )
        self.assertEqual(response.status_code, 302)
        booking = Booking.objects.get()
        self.slot_b.refresh_from_db()
        self.slot_c.refresh_from_db()
        self.assertEqual(self.slot_b.held_by_id, booking.pk)
        self.assertIsNone(self.slot_c.held_by_id)
        self.assertFalse(self.slot_b.is_open)

    def test_hides_start_times_that_cannot_fit_the_buffer(self):
        self.slot_b.delete()
        self.slot_c.delete()
        response = self.client.get(reverse("booking"), {"service": self.service.slug})
        self.assertNotContains(response, f"slot={self.slot_a.pk}")
        self.assertContains(response, "Inga lediga tider just nu")

    def test_short_treatment_fits_in_one_slot(self):
        self.service.duration_minutes = 30
        self.service.save()
        response = self.client.get(reverse("booking"), {"service": self.service.slug})
        self.assertContains(response, f"slot={self.slot_a.pk}")


class DashboardHelpTests(TestCase):
    """Staff handbook is for logged-in staff only."""

    def test_anonymous_is_sent_to_login(self):
        response = self.client.get(reverse("dashboard_help"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("/admin/login/", response["Location"])

    def test_staff_sees_swedish_handbook(self):
        from django.contrib.auth import get_user_model

        get_user_model().objects.create_user(
            "emma", "emma@example.com", "secret", is_staff=True
        )
        self.client.login(username="emma", password="secret")
        response = self.client.get(reverse("dashboard_help"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Så här sköter du hemsidan")
        self.assertContains(response, "Spara och fortsätt redigera")
        self.assertContains(response, "Hero-karusell")
        self.assertContains(response, "egentidspaservice@gmail.com")
