"""Booking domain: services, weekly schedule, slots, and customer bookings."""

from datetime import datetime, timedelta

from django.db import models
from django.utils import timezone


class Service(models.Model):
    """Bookable treatment (duration drives slot length)."""

    name = models.CharField(max_length=120)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    duration_minutes = models.PositiveIntegerField(default=60)
    price_sek = models.PositiveIntegerField(null=True, blank=True)
    image = models.ImageField(upload_to="services/", blank=True)
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "name"]
        verbose_name = "behandling"
        verbose_name_plural = "behandlingar"

    def __str__(self):
        return self.name

    def treatment_info_url(self):
        """URL to this treatment on Behandlingar & priser (#anchor), or empty if none."""
        from cms.models import ContentBlock, SitePage

        block = (
            ContentBlock.objects.filter(
                page__key=SitePage.PageKey.TREATMENTS,
                title=self.name,
                is_visible=True,
            )
            .select_related("page")
            .first()
        )
        if not block or block.is_category_heading():
            return ""
        from django.urls import reverse

        return f"{reverse('treatments')}#treatment-{block.pk}"


class WeeklyAvailability(models.Model):
    """Recurring weekday hours for booking slots and the footer Öppettider list."""

    WEEKDAYS = [
        (0, "Måndag"),
        (1, "Tisdag"),
        (2, "Onsdag"),
        (3, "Torsdag"),
        (4, "Fredag"),
        (5, "Lördag"),
        (6, "Söndag"),
    ]

    weekday = models.PositiveSmallIntegerField(
        choices=WEEKDAYS,
        verbose_name="Veckodag",
    )
    start_time = models.TimeField(verbose_name="Öppnar")
    end_time = models.TimeField(verbose_name="Stänger")
    slot_minutes = models.PositiveIntegerField(
        default=60,
        verbose_name="Passlängd (min)",
        help_text="Längd per bokningsbart pass i minuter (påverkar Boka, inte sidfotens text).",
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name="Aktiv",
        help_text="Avmarkera för att dölja dagen i sidfoten och vid luckgenerering.",
    )
    # Adjust: lunch window per weekday; empty = no lunch break that day.
    lunch_start = models.TimeField(
        verbose_name="Lunch från",
        null=True,
        blank=True,
        help_text="Lämna tomt om du inte tar lunch den dagen.",
    )
    lunch_end = models.TimeField(
        verbose_name="Lunch till",
        null=True,
        blank=True,
        help_text="Luckor under lunchen går inte att boka på Boka.",
    )

    class Meta:
        ordering = ["weekday", "start_time"]
        verbose_name = "veckoschema / öppettider"
        verbose_name_plural = "veckoschema / öppettider"
        unique_together = [("weekday", "start_time", "end_time")]

    def __str__(self):
        text = f"{self.get_weekday_display()} {self.start_time:%H:%M}–{self.end_time:%H:%M}"
        if self.lunch_start and self.lunch_end:
            text += f" (lunch {self.lunch_start:%H:%M}–{self.lunch_end:%H:%M})"
        return text

    def clean(self):
        """Lunch is optional; if used, both ends must sit inside opening hours."""
        from django.core.exceptions import ValidationError

        super().clean()
        has_start = self.lunch_start is not None
        has_end = self.lunch_end is not None
        if has_start != has_end:
            raise ValidationError(
                "Ange både Lunch från och Lunch till, eller lämna båda tomma."
            )
        if has_start and has_end:
            if self.lunch_start >= self.lunch_end:
                raise ValidationError("Lunch till måste vara efter Lunch från.")
            if self.lunch_start < self.start_time or self.lunch_end > self.end_time:
                raise ValidationError("Lunchen måste ligga inom öppettiderna.")

    def hours_display(self):
        """Open hours for the footer; splits around lunch when set."""
        if self.lunch_start and self.lunch_end:
            return (
                f"{self.start_time:%H:%M}–{self.lunch_start:%H:%M}, "
                f"{self.lunch_end:%H:%M}–{self.end_time:%H:%M}"
            )
        return f"{self.start_time:%H:%M}–{self.end_time:%H:%M}"

    def slot_overlaps_lunch(self, slot_start, slot_end):
        """True when a naive local slot interval overlaps this day's lunch."""
        if not self.lunch_start or not self.lunch_end:
            return False
        lunch_from = datetime.combine(slot_start.date(), self.lunch_start)
        lunch_to = datetime.combine(slot_start.date(), self.lunch_end)
        return slot_start < lunch_to and slot_end > lunch_from

    @classmethod
    def footer_week_rows(cls):
        """Week schedule for the site footer: one row per weekday (open hours or Stängt).

        Adjust hours in admin under Veckoschema / öppettider — saving
        updates bookable times on Boka.

        """
        active = cls.objects.filter(is_active=True).order_by("weekday", "start_time")
        ranges_by_day = {weekday: [] for weekday, _ in cls.WEEKDAYS}
        for rule in active:
            ranges_by_day[rule.weekday].append(rule.hours_display())
        rows = []
        for weekday, label in cls.WEEKDAYS:
            ranges = ranges_by_day[weekday]
            rows.append(
                {
                    "weekday": weekday,
                    "label": label,
                    "hours": ", ".join(ranges) if ranges else "Stängt",
                    "is_open": bool(ranges),
                }
            )
        return rows


def footer_opening_hours():
    """Weekday hours for the site footer, grouped when consecutive days match.

    Closed days are skipped. Returns a list of {label, hours} dicts, e.g.
    [{'label': 'Måndag–fredag', 'hours': '09:00–16:00'}].
    Edit times in admin under Veckoschema / öppettider (syncs Boka).
    """
    from collections import defaultdict

    by_day = defaultdict(list)
    for rule in WeeklyAvailability.objects.filter(is_active=True).order_by(
        "weekday", "start_time"
    ):
        by_day[rule.weekday].append(rule.hours_display())

    labels = dict(WeeklyAvailability.WEEKDAYS)
    groups = []
    current = None
    for day in range(7):
        hours = ", ".join(by_day.get(day, []))
        if not hours:
            if current:
                groups.append(current)
                current = None
            continue
        if current and current["hours"] == hours and current["end"] == day - 1:
            current["end"] = day
        else:
            if current:
                groups.append(current)
            current = {"start": day, "end": day, "hours": hours}
    if current:
        groups.append(current)

    rows = []
    for group in groups:
        start_label = labels[group["start"]]
        if group["start"] == group["end"]:
            label = start_label
        else:
            label = f"{start_label}–{labels[group['end']].lower()}"
        rows.append({"label": label, "hours": group["hours"]})
    return rows


class ClosedDate(models.Model):
    """Dates when no slots should be offered (holiday, vacation)."""

    date = models.DateField(unique=True)
    reason = models.CharField(max_length=200, blank=True)

    class Meta:
        ordering = ["date"]
        verbose_name = "stängd dag"
        verbose_name_plural = "stängda dagar"

    def __str__(self):
        return f"{self.date} ({self.reason or 'stängt'})"


class TimeSlot(models.Model):
    """A concrete bookable window on a calendar day."""

    start = models.DateTimeField()
    end = models.DateTimeField()
    is_blocked = models.BooleanField(
        default=False,
        help_text="Manuellt blockerad (syns inte som ledig).",
    )

    class Meta:
        ordering = ["start"]
        verbose_name = "tidslucka"
        verbose_name_plural = "tidsluckor"
        unique_together = [("start", "end")]

    def __str__(self):
        local = timezone.localtime(self.start)
        return local.strftime("%Y-%m-%d %H:%M")

    @property
    def is_booked(self):
        return Booking.objects.filter(slot=self, status=Booking.Status.CONFIRMED).exists()

    @property
    def is_open(self):
        """True when customers may book this slot."""
        if self.is_blocked:
            return False
        if self.start <= timezone.now():
            return False
        return not self.is_booked


class Booking(models.Model):
    """Customer reservation for a time slot and service."""

    class Status(models.TextChoices):
        CONFIRMED = "confirmed", "Bekräftad"
        CANCELLED = "cancelled", "Avbokad"

    slot = models.OneToOneField(TimeSlot, on_delete=models.CASCADE, related_name="booking")
    service = models.ForeignKey(Service, on_delete=models.PROTECT, related_name="bookings")
    customer_name = models.CharField(max_length=120)
    customer_email = models.EmailField()
    customer_phone = models.CharField(max_length=40)
    # Adjust: customer picks email and/or SMS on the booking form.
    notify_email = models.BooleanField(default=True)
    notify_sms = models.BooleanField(default=True)
    notes = models.TextField(blank=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.CONFIRMED,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "bokning"
        verbose_name_plural = "bokningar"

    def __str__(self):
        return f"{self.customer_name} – {self.slot}"


# Adjust: public /boka/ shows this many days; saving Veckoschema syncs the same window.
PUBLIC_SLOT_HORIZON_DAYS = 60


def iter_schedule_slots(start_date, end_date):
    """Yield (start, end) aware datetimes from active WeeklyAvailability.

    Skips ClosedDate days and lunch windows. Used when creating and when
    removing leftover luckor.
    """
    if end_date < start_date:
        return

    closed = set(
        ClosedDate.objects.filter(date__gte=start_date, date__lte=end_date).values_list(
            "date", flat=True
        )
    )
    weekly = list(WeeklyAvailability.objects.filter(is_active=True))
    day = start_date
    while day <= end_date:
        if day not in closed:
            for rule in weekly:
                if rule.weekday != day.weekday():
                    continue
                cursor = datetime.combine(day, rule.start_time)
                end_dt = datetime.combine(day, rule.end_time)
                step = timedelta(minutes=rule.slot_minutes)
                while cursor + step <= end_dt:
                    slot_end = cursor + step
                    if not rule.slot_overlaps_lunch(cursor, slot_end):
                        yield timezone.make_aware(cursor), timezone.make_aware(slot_end)
                    cursor = slot_end
        day += timedelta(days=1)


def generate_slots_for_range(start_date, end_date):
    """Create TimeSlot rows from active WeeklyAvailability between two dates.

    Skips ClosedDate days and does not duplicate existing (start, end) pairs.
    Returns the number of newly created slots.
    """
    created = 0
    for start_aware, end_aware in iter_schedule_slots(start_date, end_date):
        _, was_created = TimeSlot.objects.get_or_create(
            start=start_aware,
            end=end_aware,
            defaults={"is_blocked": False},
        )
        if was_created:
            created += 1
    return created


def sync_slots_for_range(start_date, end_date):
    """Make TimeSlots match Veckoschema between two dates.

    Creates missing luckor. Deletes unbooked luckor that no longer match
    (hours shortened, lunch added, day closed, or ClosedDate). Never deletes a slot that
    has a booking row. Returns (created_count, deleted_count).
    """
    created = generate_slots_for_range(start_date, end_date)
    desired = set(iter_schedule_slots(start_date, end_date))
    range_start = timezone.make_aware(datetime.combine(start_date, datetime.min.time()))
    range_end = timezone.make_aware(
        datetime.combine(end_date + timedelta(days=1), datetime.min.time())
    )
    deleted = 0
    extras = TimeSlot.objects.filter(
        start__gte=range_start,
        start__lt=range_end,
        booking__isnull=True,
    )
    for slot in extras:
        if (slot.start, slot.end) not in desired:
            slot.delete()
            deleted += 1
    return created, deleted


def sync_future_slots(days_ahead=PUBLIC_SLOT_HORIZON_DAYS):
    """Align the public Boka window with the current Veckoschema.

    Call after admin saves WeeklyAvailability or ClosedDate.
    """
    today = timezone.localdate()
    return sync_slots_for_range(today, today + timedelta(days=days_ahead))
