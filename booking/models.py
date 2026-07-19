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

    class Meta:
        ordering = ["weekday", "start_time"]
        verbose_name = "veckoschema / öppettider"
        verbose_name_plural = "veckoschema / öppettider"
        unique_together = [("weekday", "start_time", "end_time")]

    def __str__(self):
        return f"{self.get_weekday_display()} {self.start_time:%H:%M}–{self.end_time:%H:%M}"

    @classmethod
    def footer_week_rows(cls):
        """Week schedule for the site footer: one row per weekday (open hours or Stängt).

        Adjust hours in admin under Veckoschema or /dashboard/.
        """
        active = cls.objects.filter(is_active=True).order_by("weekday", "start_time")
        ranges_by_day = {weekday: [] for weekday, _ in cls.WEEKDAYS}
        for rule in active:
            ranges_by_day[rule.weekday].append(
                f"{rule.start_time:%H:%M}–{rule.end_time:%H:%M}"
            )
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
    customer_phone = models.CharField(max_length=40, blank=True)
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


def generate_slots_for_range(start_date, end_date):
    """
    Create TimeSlot rows from active WeeklyAvailability between two dates.

    Skips ClosedDate days and does not duplicate existing (start, end) pairs.
    Returns the number of newly created slots.
    """
    if end_date < start_date:
        return 0

    closed = set(ClosedDate.objects.filter(date__gte=start_date, date__lte=end_date).values_list("date", flat=True))
    weekly = list(WeeklyAvailability.objects.filter(is_active=True))
    if not weekly:
        return 0

    created = 0
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
                    start_aware = timezone.make_aware(cursor)
                    end_aware = timezone.make_aware(slot_end)
                    _, was_created = TimeSlot.objects.get_or_create(
                        start=start_aware,
                        end=end_aware,
                        defaults={"is_blocked": False},
                    )
                    if was_created:
                        created += 1
                    cursor = slot_end
        day += timedelta(days=1)
    return created
