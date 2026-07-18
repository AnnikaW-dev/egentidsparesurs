"""Unit tests for slot generation rules."""

from datetime import date, time, timedelta

from django.test import TestCase
from django.utils import timezone

from booking.models import ClosedDate, TimeSlot, WeeklyAvailability, generate_slots_for_range


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
