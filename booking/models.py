"""Booking domain: services, weekly schedule, slots, and customer bookings."""

from datetime import datetime, timedelta

from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.db.models import Q
from django.utils import timezone

# Adjust: extra minutes reserved after each treatment (cleanup / next customer).
BOOKING_BUFFER_MINUTES = 30


class Service(models.Model):
    """Bookable treatment (duration drives slot length)."""

    name = models.CharField(max_length=120)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    duration_minutes = models.PositiveIntegerField(
        default=60,
        verbose_name="Behandlingstid (min)",
        help_text="Själva behandlingen. På Boka reserveras den tiden plus 30 minuter.",
    )
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

    def calendar_minutes(self):
        """Minutes reserved on Boka: treatment length plus buffer."""
        return self.duration_minutes + BOOKING_BUFFER_MINUTES


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
        help_text=(
            "Längd per bokningsbart pass i minuter (påverkar Boka, inte sidfotens text). "
            "När du ändrar värdet byts tomma luckor ut — samma klockslag skapas aldrig två gånger. "
            "Bokade tider lämnas orörda."
        ),
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

    start = models.DateTimeField(
        unique=True,
        help_text="En lucka per starttid. Samma klockslag får inte finnas två gånger.",
    )
    end = models.DateTimeField()
    is_blocked = models.BooleanField(
        default=False,
        help_text="Manuellt blockerad (syns inte som ledig).",
    )
    held_by = models.ForeignKey(
        "Booking",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="held_slots",
        help_text="Upptagen av en längre bokning som börjar i en tidigare lucka.",
    )

    class Meta:
        ordering = ["start"]
        verbose_name = "tidslucka"
        verbose_name_plural = "tidsluckor"

    def __str__(self):
        local_start = timezone.localtime(self.start)
        local_end = timezone.localtime(self.end)
        return f"{local_start:%Y-%m-%d %H:%M}–{local_end:%H:%M}"

    def clean(self):
        """Reject a second lucka at the same start, or one that overlaps another."""
        from django.core.exceptions import ValidationError

        qs = TimeSlot.objects.filter(start=self.start)
        if self.pk:
            qs = qs.exclude(pk=self.pk)
        if qs.exists():
            raise ValidationError(
                {"start": "Det finns redan en tidslucka som börjar vid den tiden."}
            )
        if self.start and self.end:
            overlapping = TimeSlot.objects.filter(start__lt=self.end, end__gt=self.start)
            if self.pk:
                overlapping = overlapping.exclude(pk=self.pk)
            if overlapping.exists():
                raise ValidationError(
                    "Den här luckan överlappar en annan tidslucka. "
                    "Samma tid får inte finnas två gånger."
                )

    @property
    def is_booked(self):
        return Booking.objects.filter(slot=self, status=Booking.Status.CONFIRMED).exists()

    @property
    def is_open(self):
        """True when customers may start or continue a booking in this slot."""
        if self.is_blocked:
            return False
        if self.held_by_id:
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
    # Adjust: confirmation is e-post only (notify_sms kept on the row, unused).
    notify_email = models.BooleanField(default=True)
    notify_sms = models.BooleanField(default=False)
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

    def reserved_until(self):
        """End of the reserved window (treatment + buffer)."""
        return self.slot.start + timedelta(minutes=self.service.calendar_minutes())


def reserved_window_fits_hours(
    start,
    needed_minutes,
    *,
    closed_dates=None,
    rules_by_weekday=None,
):
    """True when [start, start+needed) stays inside Veckoschema hours.

    Ignores leftover TimeSlot rows, so an old 12:00 lucka cannot make 11:00
    bookable for a 90-minute reservation. Edit hours under Veckoschema.
    """
    if needed_minutes < 1:
        return False
    local_start = timezone.localtime(start)
    local_end = local_start + timedelta(minutes=needed_minutes)
    if local_end.date() != local_start.date():
        return False
    day = local_start.date()
    if closed_dates is None:
        closed = ClosedDate.objects.filter(date=day).exists()
    else:
        closed = day in closed_dates
    if closed:
        return False
    if rules_by_weekday is None:
        rules = list(
            WeeklyAvailability.objects.filter(weekday=day.weekday(), is_active=True)
        )
    else:
        rules = rules_by_weekday.get(day.weekday(), [])
    if not rules:
        # No Veckoschema for this weekday — fall back to slot chaining only.
        return True
    start_t = local_start.time()
    end_t = local_end.time()
    win_from = datetime.combine(day, start_t)
    win_to = datetime.combine(day, end_t)
    for rule in rules:
        if start_t < rule.start_time or end_t > rule.end_time:
            continue
        if rule.slot_overlaps_lunch(win_from, win_to):
            continue
        return True
    return False


def occupied_intervals():
    """Ranges already taken: confirmed bookings (treatment + buffer), holds, blocks."""
    intervals = []
    for booking in Booking.objects.filter(status=Booking.Status.CONFIRMED).select_related(
        "service", "slot"
    ):
        intervals.append((booking.slot.start, booking.reserved_until()))
    for slot in TimeSlot.objects.filter(Q(is_blocked=True) | Q(held_by__isnull=False)):
        intervals.append((slot.start, slot.end))
    return intervals


def window_hits_occupied(start, needed_minutes, intervals):
    """True when [start, start+needed) overlaps an occupied range."""
    needed_end = start + timedelta(minutes=needed_minutes)
    return any(occ_start < needed_end and occ_end > start for occ_start, occ_end in intervals)


def can_start_service(
    start_slot,
    service,
    open_by_start=None,
    *,
    closed_dates=None,
    rules_by_weekday=None,
):
    """True when this start has treatment length plus buffer still free."""
    needed = service.calendar_minutes()
    if not slot_run_covering(start_slot, needed, open_by_start=open_by_start):
        return False
    if window_hits_occupied(start_slot.start, needed, occupied_intervals()):
        return False
    return reserved_window_fits_hours(
        start_slot.start,
        needed,
        closed_dates=closed_dates,
        rules_by_weekday=rules_by_weekday,
    )


def bookable_start_slots(service, slots=None):
    """Start times to show for this treatment on Boka and in admin klockslag."""
    slots = list(slots if slots is not None else upcoming_open_slots())
    needed = service.calendar_minutes()
    open_by_start = {int(slot.start.timestamp()): slot for slot in slots}
    taken = occupied_intervals()
    today = timezone.localdate()
    closed_dates = set(
        ClosedDate.objects.filter(
            date__gte=today,
            date__lte=today + timedelta(days=PUBLIC_SLOT_HORIZON_DAYS),
        ).values_list("date", flat=True)
    )
    rules_by_weekday = {}
    for rule in WeeklyAvailability.objects.filter(is_active=True):
        rules_by_weekday.setdefault(rule.weekday, []).append(rule)
    return [
        slot
        for slot in slots
        if slot_run_covering(slot, needed, open_by_start=open_by_start)
        and not window_hits_occupied(slot.start, needed, taken)
        and reserved_window_fits_hours(
            slot.start,
            needed,
            closed_dates=closed_dates,
            rules_by_weekday=rules_by_weekday,
        )
    ]


def slot_run_covering(start_slot, needed_minutes, open_by_start=None):
    """Return contiguous open slots from start_slot that cover needed_minutes.

    Slots must chain (next.start == previous.end). Returns [] if there is a
    gap, lunch, closing time, or a taken slot before the window is full.
    """
    if needed_minutes < 1 or not start_slot.is_open:
        return []
    needed_end = start_slot.start + timedelta(minutes=needed_minutes)
    run = [start_slot]
    covered_end = start_slot.end
    while covered_end < needed_end:
        if open_by_start is not None:
            nxt = open_by_start.get(int(covered_end.timestamp()))
        else:
            nxt = TimeSlot.objects.filter(start=covered_end).first()
        if nxt is None or not nxt.is_open:
            return []
        run.append(nxt)
        covered_end = nxt.end
    return run


def occupy_slot_run(booking, run):
    """Mark extra slots in the run as held by this booking (first slot is booking.slot)."""
    for extra in run[1:]:
        extra.held_by = booking
        extra.save(update_fields=["held_by"])


def create_confirmed_booking(
    *,
    service,
    start_slot,
    customer_name,
    customer_email,
    customer_phone,
    notify_email=True,
    notify_sms=False,
    notes="",
):
    """Save a booking and reserve treatment length plus buffer.

    Reuses a cancelled row on the same slot. Raises ValidationError if the
    start time is taken or too short for the service.
    """
    needed = service.calendar_minutes()
    taken_msg = "Den tiden räcker inte för behandlingen, eller är inte ledig."
    with transaction.atomic():
        existing = (
            Booking.objects.select_for_update().filter(slot_id=start_slot.pk).first()
        )
        if existing and existing.status == Booking.Status.CONFIRMED:
            raise ValidationError(taken_msg)
        if existing:
            TimeSlot.objects.filter(held_by=existing).update(held_by=None)
        tentative = slot_run_covering(
            TimeSlot.objects.select_for_update().get(pk=start_slot.pk),
            needed,
        )
        if (
            not tentative
            or not reserved_window_fits_hours(start_slot.start, needed)
            or window_hits_occupied(start_slot.start, needed, occupied_intervals())
        ):
            raise ValidationError(taken_msg)
        locked = list(
            TimeSlot.objects.select_for_update()
            .filter(pk__in=[slot.pk for slot in tentative])
            .order_by("start")
        )
        if not locked or locked[0].pk != start_slot.pk:
            raise ValidationError(taken_msg)
        start = locked[0]
        run = slot_run_covering(start, needed)
        if [slot.pk for slot in run] != [slot.pk for slot in locked]:
            raise ValidationError(taken_msg)
        values = {
            "service": service,
            "customer_name": customer_name,
            "customer_email": customer_email,
            "customer_phone": customer_phone,
            "notify_email": notify_email,
            "notify_sms": notify_sms,
            "notes": notes,
            "status": Booking.Status.CONFIRMED,
        }
        if existing:
            booking = existing
            for field, value in values.items():
                setattr(booking, field, value)
            booking.save()
        else:
            booking = Booking.objects.create(slot=start, **values)
        occupy_slot_run(booking, run)
        return booking


# Adjust: public /boka/ and admin klockslag; ~6 months, kept in sync with Veckoschema.
PUBLIC_SLOT_HORIZON_DAYS = 183


def upcoming_open_slots():
    """Slots staff or customers may start a booking in (same window as Boka)."""
    now = timezone.now()
    return (
        TimeSlot.objects.filter(
            start__gte=now,
            start__lte=now + timedelta(days=PUBLIC_SLOT_HORIZON_DAYS),
            is_blocked=False,
            held_by__isnull=True,
        )
        .exclude(booking__status=Booking.Status.CONFIRMED)
        .order_by("start")
    )


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


def _slot_is_busy(slot):
    """True when this lucka belongs to a booking — never delete or change start/end."""
    if slot.held_by_id:
        return True
    return Booking.objects.filter(slot_id=slot.pk).exists()


def _busy_slot_windows():
    """(start, end) for luckor with a booking or hold — empty luckor must not overlay these."""
    return [
        (slot.start, slot.end)
        for slot in TimeSlot.objects.filter(
            Q(held_by__isnull=False) | Q(booking__isnull=False)
        )
    ]


def _overlaps_any_window(start, end, windows):
    """True when [start, end) shares time with any (other_start, other_end) pair."""
    return any(start < other_end and end > other_start for other_start, other_end in windows)


def _pick_timeslot_to_keep(rows):
    """Choose one row when several luckor share a start time."""
    confirmed = [
        slot
        for slot in rows
        if Booking.objects.filter(slot_id=slot.pk, status=Booking.Status.CONFIRMED).exists()
    ]
    if confirmed:
        return confirmed[0]
    busy = [slot for slot in rows if _slot_is_busy(slot)]
    if busy:
        return busy[0]
    day = timezone.localtime(rows[0].start).date()
    desired_ends = {
        end for start, end in iter_schedule_slots(day, day) if start == rows[0].start
    }
    matching = [slot for slot in rows if slot.end in desired_ends]
    if matching:
        return matching[0]
    return min(rows, key=lambda slot: ((slot.end - slot.start), slot.pk))


def dedupe_timeslots_with_same_start():
    """Delete extra luckor that share a start time. Keep booked/held rows.

    Old 60-minute luckor plus new 30-minute luckor at the same clock looked like
    duplicates in admin. Call before enforcing unique(start).
    Returns how many rows were deleted.
    """
    from collections import defaultdict

    grouped = defaultdict(list)
    for slot in TimeSlot.objects.order_by("pk"):
        grouped[slot.start].append(slot)
    deleted = 0
    for rows in grouped.values():
        if len(rows) < 2:
            continue
        keep = _pick_timeslot_to_keep(rows)
        for slot in rows:
            if slot.pk == keep.pk or _slot_is_busy(slot):
                continue
            slot.delete()
            deleted += 1
    return deleted


def generate_slots_for_range(start_date, end_date):
    """Create TimeSlot rows from active WeeklyAvailability between two dates.

    One lucka per start time (unique start). Booked or held luckor keep their
    start and end. New empty luckor are not created on top of a booked window.
    Returns the number of newly created slots.
    """
    created = 0
    busy_windows = _busy_slot_windows()
    for start_aware, end_aware in iter_schedule_slots(start_date, end_date):
        slot = TimeSlot.objects.filter(start=start_aware).first()
        if slot is not None:
            if _slot_is_busy(slot):
                continue
            if slot.end != end_aware:
                slot.end = end_aware
                slot.save(update_fields=["end"])
            continue
        # Adjust: passlängd change must not add a second lucka over a booking.
        if _overlaps_any_window(start_aware, end_aware, busy_windows):
            continue
        TimeSlot.objects.create(
            start=start_aware,
            end=end_aware,
            is_blocked=False,
        )
        created += 1
    return created


def sync_slots_for_range(start_date, end_date):
    """Make TimeSlots match Veckoschema between two dates.

    Creates missing luckor. Deletes unbooked luckor that no longer match
    (hours shortened, lunch added, day closed, ClosedDate, or passlängd
    changed). Never two luckor at the same start. Never deletes, resizes, or
    overlays a lucka that has a booking or a hold. Returns (created_count,
    deleted_count).
    """
    deleted = dedupe_timeslots_with_same_start()
    created = generate_slots_for_range(start_date, end_date)
    desired = set(iter_schedule_slots(start_date, end_date))
    busy_windows = _busy_slot_windows()
    range_start = timezone.make_aware(datetime.combine(start_date, datetime.min.time()))
    range_end = timezone.make_aware(
        datetime.combine(end_date + timedelta(days=1), datetime.min.time())
    )
    extras = TimeSlot.objects.filter(
        start__gte=range_start,
        start__lt=range_end,
        booking__isnull=True,
        held_by__isnull=True,
    )
    for slot in extras:
        if _slot_is_busy(slot):
            continue
        stale_length = (slot.start, slot.end) not in desired
        overlays_booking = _overlaps_any_window(slot.start, slot.end, busy_windows)
        if stale_length or overlays_booking:
            slot.delete()
            deleted += 1
    return created, deleted


def sync_future_slots(days_ahead=PUBLIC_SLOT_HORIZON_DAYS):
    """Align the public Boka window with the current Veckoschema.

    Call after admin saves WeeklyAvailability or ClosedDate.
    """
    today = timezone.localdate()
    return sync_slots_for_range(today, today + timedelta(days=days_ahead))
