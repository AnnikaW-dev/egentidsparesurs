"""Unit tests for slot generation and booking confirmation email."""

from datetime import date, time, timedelta

from django.core import mail
from django.db import IntegrityError
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from booking.models import Booking, ClosedDate, Service, TimeSlot, WeeklyAvailability, generate_slots_for_range


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


class TimeSlotUniqueStartTests(TestCase):
    """Admin Tidsluckor must never list two luckor that start at the same clock."""

    def test_database_rejects_a_second_slot_at_the_same_start(self):
        start = timezone.now() + timedelta(days=5)
        TimeSlot.objects.create(start=start, end=start + timedelta(minutes=30))
        with self.assertRaises(IntegrityError):
            TimeSlot.objects.create(start=start, end=start + timedelta(hours=1))

    def test_sync_does_not_add_another_row_when_a_booked_start_has_the_old_length(self):
        from booking.models import generate_slots_for_range, sync_slots_for_range

        monday = timezone.localdate() + timedelta(days=14)
        while monday.weekday() != 0:
            monday += timedelta(days=1)
        rule = WeeklyAvailability.objects.create(
            weekday=0,
            start_time=time(9, 0),
            end_time=time(12, 0),
            slot_minutes=60,
            is_active=True,
        )
        generate_slots_for_range(monday, monday)
        first = TimeSlot.objects.order_by("start").first()
        service = Service.objects.create(
            name="Spa",
            slug="spa-unique-start",
            duration_minutes=60,
            is_active=True,
        )
        Booking.objects.create(
            slot=first,
            service=service,
            customer_name="Anna",
            customer_email="anna@example.com",
            customer_phone="0701234567",
        )
        rule.slot_minutes = 30
        rule.save()
        sync_slots_for_range(monday, monday)
        self.assertEqual(TimeSlot.objects.filter(start=first.start).count(), 1)

    def test_sync_does_not_change_an_existing_booking_time(self):
        from booking.models import create_confirmed_booking, sync_slots_for_range

        monday = timezone.localdate() + timedelta(days=14)
        while monday.weekday() != 0:
            monday += timedelta(days=1)
        WeeklyAvailability.objects.create(
            weekday=0,
            start_time=time(9, 0),
            end_time=time(16, 0),
            slot_minutes=30,
            is_active=True,
            lunch_start=time(12, 0),
            lunch_end=time(13, 0),
        )
        from booking.models import generate_slots_for_range

        generate_slots_for_range(monday, monday)
        start_slot = TimeSlot.objects.order_by("start").first()
        service = Service.objects.create(
            name="Spa",
            slug="spa-keep-booking",
            duration_minutes=60,
            is_active=True,
        )
        booking = create_confirmed_booking(
            service=service,
            start_slot=start_slot,
            customer_name="Kalle",
            customer_email="kalle@example.com",
            customer_phone="0701234567",
            notify_email=False,
        )
        slot_id = booking.slot_id
        start = booking.slot.start
        end = booking.slot.end
        held_ids = list(
            TimeSlot.objects.filter(held_by=booking).values_list("pk", "start", "end")
        )
        sync_slots_for_range(monday, monday)
        booking.refresh_from_db()
        booking.slot.refresh_from_db()
        self.assertEqual(booking.slot_id, slot_id)
        self.assertEqual(booking.slot.start, start)
        self.assertEqual(booking.slot.end, end)
        self.assertEqual(booking.customer_name, "Kalle")
        self.assertEqual(booking.status, Booking.Status.CONFIRMED)
        after_held = list(
            TimeSlot.objects.filter(held_by=booking).values_list("pk", "start", "end")
        )
        self.assertEqual(after_held, held_ids)

    def test_changing_passlangd_replaces_empty_slots_without_duplicate_starts(self):
        from booking.models import generate_slots_for_range, sync_slots_for_range

        monday = timezone.localdate() + timedelta(days=14)
        while monday.weekday() != 0:
            monday += timedelta(days=1)
        rule = WeeklyAvailability.objects.create(
            weekday=0,
            start_time=time(9, 0),
            end_time=time(12, 0),
            slot_minutes=60,
            is_active=True,
        )
        generate_slots_for_range(monday, monday)
        self.assertEqual(TimeSlot.objects.count(), 3)

        rule.slot_minutes = 30
        rule.save()
        sync_slots_for_range(monday, monday)
        starts = list(TimeSlot.objects.values_list("start", flat=True))
        self.assertEqual(len(starts), len(set(starts)))
        self.assertEqual(len(starts), 6)
        for slot in TimeSlot.objects.all():
            self.assertEqual(slot.end - slot.start, timedelta(minutes=30))

        rule.slot_minutes = 60
        rule.save()
        sync_slots_for_range(monday, monday)
        starts = list(TimeSlot.objects.values_list("start", flat=True))
        self.assertEqual(len(starts), len(set(starts)))
        self.assertEqual(len(starts), 3)
        for slot in TimeSlot.objects.all():
            self.assertEqual(slot.end - slot.start, timedelta(minutes=60))

    def test_changing_passlangd_does_not_overlay_a_booked_lucka(self):
        from booking.models import generate_slots_for_range, sync_slots_for_range

        monday = timezone.localdate() + timedelta(days=14)
        while monday.weekday() != 0:
            monday += timedelta(days=1)
        rule = WeeklyAvailability.objects.create(
            weekday=0,
            start_time=time(9, 0),
            end_time=time(12, 0),
            slot_minutes=60,
            is_active=True,
        )
        generate_slots_for_range(monday, monday)
        booked = TimeSlot.objects.order_by("start").first()
        service = Service.objects.create(
            name="Spa",
            slug="spa-no-overlay",
            duration_minutes=60,
            is_active=True,
        )
        Booking.objects.create(
            slot=booked,
            service=service,
            customer_name="Anna",
            customer_email="anna@example.com",
            customer_phone="0701234567",
        )
        rule.slot_minutes = 30
        rule.save()
        sync_slots_for_range(monday, monday)

        starts = list(TimeSlot.objects.values_list("start", flat=True))
        self.assertEqual(len(starts), len(set(starts)))
        booked.refresh_from_db()
        self.assertEqual(booked.end - booked.start, timedelta(hours=1))
        half_hour = booked.start + timedelta(minutes=30)
        self.assertFalse(TimeSlot.objects.filter(start=half_hour).exists())

    def test_admin_form_rejects_a_second_slot_at_the_same_start(self):
        from django.core.exceptions import ValidationError

        start = timezone.now() + timedelta(days=5)
        TimeSlot.objects.create(start=start, end=start + timedelta(minutes=30))
        duplicate = TimeSlot(
            start=start,
            end=start + timedelta(hours=1),
        )
        with self.assertRaises(ValidationError):
            duplicate.full_clean()


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


class BookingConfirmationNotifyTests(TestCase):
    """Public bookings always confirm by e-post and copy staff. SMS is not sent."""

    def setUp(self):
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

    def _post(self, extra=None):
        data = {
            "service": self.service.slug,
            "slot": self.slot.pk,
            "customer_name": "Anna Test",
            "customer_email": "anna@example.com",
            "customer_phone": "0701234567",
        }
        if extra:
            data.update(extra)
        return self.client.post(reverse("booking"), data)

    def test_booking_sends_customer_and_staff_email(self):
        response = self._post()
        self.assertEqual(Booking.objects.count(), 1)
        booking = Booking.objects.get()
        self.assertTrue(booking.notify_email)
        self.assertFalse(booking.notify_sms)
        self.assertRedirects(response, reverse("booking_success", kwargs={"pk": booking.pk}))
        self.assertEqual(len(mail.outbox), 2)
        recipients = {tuple(m.to) for m in mail.outbox}
        self.assertEqual(
            recipients,
            {("anna@example.com",), ("egentidspaservice@gmail.com",)},
        )

    def test_public_form_has_no_sms_choice(self):
        response = self.client.get(
            reverse("booking"),
            {"service": self.service.slug, "slot": self.slot.pk},
        )
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "SMS")
        self.assertNotContains(response, "confirm_via")

    def test_success_page_mentions_email_not_sms(self):
        self._post()
        booking = Booking.objects.get()
        response = self.client.get(reverse("booking_success", kwargs={"pk": booking.pk}))
        self.assertContains(response, "En bekräftelse har skickats till")
        self.assertContains(response, "anna@example.com")
        self.assertNotContains(response, "SMS")
        self.assertContains(response, "0701234567")


class BookingDurationBufferTests(TestCase):
    """A booking reserves treatment length plus 30 minutes of calendar slots."""

    def setUp(self):
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

    def test_public_page_does_not_mention_the_buffer(self):
        response = self.client.get(reverse("booking"))
        self.assertNotContains(response, "+ 30 min")
        self.assertNotContains(response, "Vi reserverar")
        self.assertContains(response, "60 min")


class BookingHidesShortWindowsTests(TestCase):
    """Do not offer starts that cannot fit treatment length plus 30 minutes."""

    def setUp(self):
        self.monday = timezone.localdate() + timedelta(days=7)
        while self.monday.weekday() != 0:
            self.monday += timedelta(days=1)
        WeeklyAvailability.objects.create(
            weekday=0,
            start_time=time(9, 0),
            end_time=time(16, 0),
            slot_minutes=30,
            is_active=True,
            lunch_start=time(12, 0),
            lunch_end=time(13, 0),
        )
        from booking.models import sync_slots_for_range

        sync_slots_for_range(self.monday, self.monday)
        self.service = Service.objects.create(
            name="Spa",
            slug="spa",
            duration_minutes=60,
            is_active=True,
        )

    def _slot_at(self, hour, minute):
        for slot in TimeSlot.objects.order_by("start"):
            local = timezone.localtime(slot.start)
            if local.date() == self.monday and local.hour == hour and local.minute == minute:
                return slot
        self.fail(f"No slot at {hour:02d}:{minute:02d}")

    def test_public_hides_starts_before_lunch_and_closing(self):
        response = self.client.get(reverse("booking"), {"service": self.service.slug})
        self.assertContains(response, f"slot={self._slot_at(10, 30).pk}")
        self.assertContains(response, f"slot={self._slot_at(14, 30).pk}")
        self.assertNotContains(response, f"slot={self._slot_at(11, 0).pk}")
        self.assertNotContains(response, f"slot={self._slot_at(11, 30).pk}")
        self.assertNotContains(response, f"slot={self._slot_at(15, 0).pk}")
        self.assertNotContains(response, f"slot={self._slot_at(15, 30).pk}")

    def test_leftover_lunch_slot_does_not_show_a_late_morning_start(self):
        from datetime import datetime

        noon = timezone.make_aware(datetime.combine(self.monday, time(12, 0)))
        TimeSlot.objects.get_or_create(
            start=noon,
            end=noon + timedelta(minutes=30),
            defaults={"is_blocked": False},
        )
        response = self.client.get(reverse("booking"), {"service": self.service.slug})
        self.assertNotContains(response, f"slot={self._slot_at(11, 0).pk}")

    def test_staff_klockslag_omits_starts_that_do_not_fit(self):
        import json
        import re

        from django.contrib.auth import get_user_model

        get_user_model().objects.create_superuser("emma", "emma@example.com", "secret")
        self.client.login(username="emma", password="secret")
        response = self.client.get(reverse("admin:booking_booking_add"))
        match = re.search(
            r'id="staff-booking-slots">(?P<json>.*?)</script>',
            response.content.decode(),
            re.S,
        )
        self.assertIsNotNone(match)
        payload = json.loads(match.group("json"))
        times = [item["time"] for item in payload[str(self.service.pk)].get(self.monday.isoformat(), [])]
        self.assertIn("10:30", times)
        self.assertIn("14:30", times)
        self.assertNotIn("11:00", times)
        self.assertNotIn("15:30", times)

    def test_hides_1230_when_the_next_booking_leaves_too_little_room(self):
        """A 12:30 chip before a 13:00 booking is only 30 minutes — too short."""
        from datetime import datetime

        from booking.models import create_confirmed_booking

        for hour, minute in ((12, 0), (12, 30), (16, 0), (16, 30)):
            start = timezone.make_aware(datetime.combine(self.monday, time(hour, minute)))
            TimeSlot.objects.get_or_create(
                start=start,
                end=start + timedelta(minutes=30),
                defaults={"is_blocked": False},
            )
        create_confirmed_booking(
            service=self.service,
            start_slot=self._slot_at(13, 0),
            customer_name="Kalle",
            customer_email="kalle@example.com",
            customer_phone="0701234567",
            notify_email=False,
        )
        short = Service.objects.create(
            name="Massage",
            slug="massage",
            duration_minutes=30,
            is_active=True,
        )
        for slug in (self.service.slug, short.slug):
            response = self.client.get(reverse("booking"), {"service": slug})
            self.assertNotContains(response, f"slot={self._slot_at(12, 30).pk}")
            self.assertNotContains(response, f"slot={self._slot_at(12, 0).pk}")
            self.assertNotContains(response, f"slot={self._slot_at(16, 0).pk}")

    def test_hides_a_long_leftover_slot_that_overlaps_the_next_booking(self):
        from datetime import datetime

        from booking.models import create_confirmed_booking

        start = timezone.make_aware(datetime.combine(self.monday, time(12, 30)))
        TimeSlot.objects.filter(start=start).delete()
        fat = TimeSlot.objects.create(start=start, end=start + timedelta(hours=3, minutes=30))
        create_confirmed_booking(
            service=self.service,
            start_slot=self._slot_at(13, 0),
            customer_name="Kalle",
            customer_email="kalle@example.com",
            customer_phone="0701234567",
            notify_email=False,
        )
        response = self.client.get(reverse("booking"), {"service": self.service.slug})
        self.assertNotContains(response, f"slot={fat.pk}")


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
        self.assertContains(response, "Boka in en kund")
        self.assertContains(response, "Lägg till bokning")
        self.assertContains(response, "datum")
        self.assertContains(response, "klockslag")


class AdminStaffBookingTests(TestCase):
    """Staff can book a customer in Django admin with the same duration+buffer rules."""

    def setUp(self):
        from django.contrib.auth import get_user_model

        get_user_model().objects.create_superuser("emma", "emma@example.com", "secret")
        self.client.login(username="emma", password="secret")
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
        self.slot_d = TimeSlot.objects.create(
            start=start + timedelta(hours=3),
            end=start + timedelta(hours=4),
        )

    def test_add_form_explains_the_flow(self):
        response = self.client.get(reverse("admin:booking_booking_add"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Boka in kund")
        self.assertContains(response, "Behandling")
        self.assertContains(response, "behandlingstiden plus 30 minuter")
        self.assertContains(response, "Datum")
        self.assertContains(response, "Klockslag")
        self.assertContains(response, 'type="date"')
        self.assertContains(response, "admin-staff-booking.js")
        self.assertContains(response, 'id="staff-booking-slots"')
        self.assertNotContains(response, "SMS")

    def test_preselects_slot_from_query_string(self):
        local = timezone.localtime(self.slot_a.start)
        response = self.client.get(
            reverse("admin:booking_booking_add"),
            {"slot": self.slot_a.pk},
        )
        self.assertContains(response, f'value="{local.date().isoformat()}"')
        self.assertContains(
            response,
            f'<option value="{self.slot_a.pk}" selected>',
            html=False,
        )

    def test_timeslot_list_has_book_customer_link(self):
        response = self.client.get(reverse("admin:booking_timeslot_changelist"))
        self.assertContains(response, "Boka kund")
        self.assertContains(
            response,
            f"{reverse('admin:booking_booking_add')}?slot={self.slot_a.pk}",
        )

    def test_admin_add_holds_the_buffer_and_hides_public_starts(self):
        local = timezone.localtime(self.slot_a.start)
        response = self.client.post(
            reverse("admin:booking_booking_add"),
            {
                "service": self.service.pk,
                "booking_date": local.date().isoformat(),
                "booking_time": str(self.slot_a.pk),
                "customer_name": "Britt",
                "customer_email": "britt@example.com",
                "customer_phone": "0701234567",
                "notify_email": "on",
                "notes": "Ringde in",
                "_save": "Spara",
            },
        )
        self.assertEqual(response.status_code, 302)
        booking = Booking.objects.get()
        self.assertEqual(booking.customer_name, "Britt")
        self.assertEqual(booking.notes, "Ringde in")
        self.assertTrue(booking.notify_email)
        self.assertFalse(booking.notify_sms)
        self.slot_b.refresh_from_db()
        self.slot_c.refresh_from_db()
        self.assertEqual(self.slot_b.held_by_id, booking.pk)
        self.assertIsNone(self.slot_c.held_by_id)
        public = self.client.get(reverse("booking"), {"service": self.service.slug})
        self.assertNotContains(public, f"slot={self.slot_a.pk}")
        self.assertNotContains(public, f"slot={self.slot_b.pk}")
        self.assertContains(public, f"slot={self.slot_c.pk}")

    def test_rejects_start_that_does_not_fit(self):
        self.slot_b.delete()
        self.slot_c.delete()
        self.slot_d.delete()
        local = timezone.localtime(self.slot_a.start)
        response = self.client.post(
            reverse("admin:booking_booking_add"),
            {
                "service": self.service.pk,
                "booking_date": local.date().isoformat(),
                "booking_time": str(self.slot_a.pk),
                "customer_name": "Britt",
                "customer_email": "britt@example.com",
                "customer_phone": "0701234567",
                "notify_email": "on",
                "_save": "Spara",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Den tiden räcker inte för behandlingen")
        self.assertFalse(Booking.objects.exists())

    def test_cancel_releases_held_slots(self):
        from booking.models import create_confirmed_booking

        booking = create_confirmed_booking(
            service=self.service,
            start_slot=self.slot_a,
            customer_name="Britt",
            customer_email="britt@example.com",
            customer_phone="0701234567",
            notify_email=False,
            notify_sms=False,
        )
        response = self.client.post(
            reverse("admin:booking_booking_changelist"),
            {
                "action": "cancel_bookings",
                "_selected_action": [str(booking.pk)],
                "index": "0",
            },
        )
        self.assertEqual(response.status_code, 302)
        booking.refresh_from_db()
        self.slot_b.refresh_from_db()
        self.assertEqual(booking.status, Booking.Status.CANCELLED)
        self.assertIsNone(self.slot_b.held_by_id)

    def test_warns_when_there_are_no_open_slots(self):
        TimeSlot.objects.all().delete()
        response = self.client.get(reverse("admin:booking_booking_add"))
        self.assertContains(response, "Inga lediga tider att välja")
        self.assertContains(response, "Veckoschema")

