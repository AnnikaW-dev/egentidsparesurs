"""Public booking views and staff availability dashboard."""

from calendar import monthrange
from datetime import date, datetime, time, timedelta

from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from cms.models import SitePage

from .forms import (
    AvailabilityGenerateForm,
    BookingForm,
    PhoneBookingForm,
    QuickWeekForm,
    StaffSlotForm,
)
from .models import (
    PUBLIC_SLOT_HORIZON_DAYS,
    Booking,
    Service,
    TimeSlot,
    WeeklyAvailability,
    add_staff_slot,
    bookable_start_slots,
    can_start_service,
    cancel_booking,
    create_confirmed_booking,
    remove_open_slot,
    sync_future_slots,
    sync_slots_for_range,
    upcoming_open_slots,
)
from .notifications import send_booking_notifications


def _booking_query(request):
    """Read selected service/slot from GET or POST."""
    service_slug = request.GET.get("service") or request.POST.get("service")
    slot_id = request.GET.get("slot") or request.POST.get("slot")
    return service_slug, slot_id


def _monday_of(day):
    """Monday of the calendar week that contains this local date."""
    return day - timedelta(days=day.weekday())


def _booking_week(raw):
    """Monday to show on public Boka, kept inside the bookable horizon.

    Empty or invalid values become this week's Monday. A date later in the
    week snaps back to that week's Monday.
    """
    today = timezone.localdate()
    horizon_end = today + timedelta(days=PUBLIC_SLOT_HORIZON_DAYS)
    first = _monday_of(today)
    last = _monday_of(horizon_end)
    if not raw:
        return first
    try:
        chosen = date.fromisoformat(str(raw))
    except ValueError:
        return first
    monday = _monday_of(chosen)
    if monday < first:
        return first
    if monday > last:
        return last
    return monday


def _public_week_url(service, week_monday):
    """Public Boka URL for one treatment and one week (the Monday)."""
    return (
        f"{reverse('booking')}?service={service.slug}&week={week_monday.isoformat()}"
    )


def _bookable_in_week(service, week_monday):
    """Start times Mon–Sun that fit this treatment.

    Only this week's luckor are loaded. A treatment cannot cross midnight, so
    Sunday starts do not need Monday's slots.
    """
    start = timezone.make_aware(datetime.combine(week_monday, time.min))
    end = start + timedelta(days=7)
    window_start = start if start > timezone.now() else timezone.now()
    candidates = upcoming_open_slots().filter(start__gte=window_start, start__lt=end)
    return bookable_start_slots(service, candidates)


def booking_page(request):
    """Three-step booking: 1) treatment 2) one week of times 3) name + phone.

    Step 2 shows a single Monday–Sunday week. `week` is that Monday (YYYY-MM-DD).
    Customers move with Föregående vecka / Nästa vecka, up to PUBLIC_SLOT_HORIZON_DAYS.
    """
    page = SitePage.objects.filter(key=SitePage.PageKey.BOOKING, is_published=True).first()
    services = Service.objects.filter(is_active=True)
    service_slug, slot_id = _booking_query(request)

    selected_service = None
    if service_slug:
        selected_service = get_object_or_404(Service, slug=service_slug, is_active=True)

    selected_slot = None
    if slot_id and selected_service:
        selected_slot = get_object_or_404(TimeSlot, pk=slot_id)
        if not can_start_service(selected_slot, selected_service):
            messages.error(
                request,
                "Den tiden räcker inte för behandlingen, eller är inte längre ledig. Välj en annan lucka.",
            )
            week = _monday_of(timezone.localtime(selected_slot.start).date())
            return redirect(_public_week_url(selected_service, week))

    by_date = {}
    week_monday = None
    prev_week = None
    next_week = None
    if selected_service and selected_slot is None:
        raw_week = request.GET.get("week")
        week_monday = _booking_week(raw_week)
        if request.method == "GET" and raw_week and raw_week != week_monday.isoformat():
            return redirect(_public_week_url(selected_service, week_monday))
        for slot in _bookable_in_week(selected_service, week_monday):
            local = timezone.localtime(slot.start)
            by_date.setdefault(local.date(), []).append(slot)
        today = timezone.localdate()
        first_week = _monday_of(today)
        last_week = _monday_of(today + timedelta(days=PUBLIC_SLOT_HORIZON_DAYS))
        if week_monday > first_week:
            prev_week = week_monday - timedelta(days=7)
        if week_monday < last_week:
            next_week = week_monday + timedelta(days=7)
    elif selected_slot:
        week_monday = _monday_of(timezone.localtime(selected_slot.start).date())

    form = None
    booking_step = 1
    if selected_service and selected_slot:
        booking_step = 3
    elif selected_service:
        booking_step = 2

    if request.method == "POST" and selected_service and selected_slot:
        form = BookingForm(request.POST, service=selected_service)
        if form.is_valid():
            try:
                booking = create_confirmed_booking(
                    service=selected_service,
                    start_slot=selected_slot,
                    customer_name=form.cleaned_data["customer_name"],
                    customer_email=form.cleaned_data["customer_email"],
                    customer_phone=form.cleaned_data["customer_phone"],
                    notify_email=True,
                    notify_sms=False,
                )
            except ValidationError:
                messages.error(request, "Den tiden just bokades av någon annan.")
                return redirect(_public_week_url(selected_service, week_monday))
            start_slot = booking.slot
            notify = send_booking_notifications(booking)
            request.session["booking_notify"] = notify
            messages.success(
                request,
                f"Tack {booking.customer_name}! Din tid {timezone.localtime(start_slot.start):%Y-%m-%d %H:%M} är bokad.",
            )
            if notify.get("email") is False:
                messages.warning(
                    request,
                    "Bokningen sparades men bekräftelsemejlet kunde inte skickas.",
                )
            return redirect("booking_success", pk=booking.pk)
    elif selected_service and selected_slot:
        form = BookingForm(service=selected_service)

    return render(
        request,
        "booking/book.html",
        {
            "page": page,
            "services": services,
            "selected_service": selected_service,
            "slots_by_date": sorted(by_date.items()),
            "form": form,
            "selected_slot": selected_slot,
            "booking_step": booking_step,
            "week_monday": week_monday,
            "week_sunday": week_monday + timedelta(days=6) if week_monday else None,
            "week_number": week_monday.isocalendar()[1] if week_monday else None,
            "prev_week": prev_week,
            "next_week": next_week,
        },
    )


def booking_success(request, pk):
    """Confirmation page after a successful booking."""
    booking = get_object_or_404(Booking, pk=pk)
    notify = request.session.pop("booking_notify", {})
    return render(
        request,
        "booking/success.html",
        {
            "booking": booking,
            "email_sent": notify.get("email"),
        },
    )


def _parse_staff_day(raw):
    """A date inside the public Boka window. Invalid or past values become today."""
    today = timezone.localdate()
    last = today + timedelta(days=PUBLIC_SLOT_HORIZON_DAYS)
    if not raw:
        return today
    try:
        chosen = date.fromisoformat(str(raw))
    except ValueError:
        return today
    if chosen < today:
        return today
    if chosen > last:
        return last
    return chosen


def _phone_day_url(service, day):
    """Dashboard phone-booking URL for one treatment and one local day."""
    return (
        f"{reverse('dashboard_phone_booking')}"
        f"?service={service.slug}&day={day.isoformat()}"
    )


def _bookable_on_day(service, day):
    """Start times on this local day that still fit the treatment plus buffer."""
    start = timezone.make_aware(datetime.combine(day, time.min))
    end = start + timedelta(days=1)
    window_start = start if start > timezone.now() else timezone.now()
    candidates = upcoming_open_slots().filter(start__gte=window_start, start__lt=end)
    return bookable_start_slots(service, candidates)


@staff_member_required
@require_http_methods(["GET", "POST"])
def dashboard_phone_booking(request):
    """Book a customer who calls. The reserved time disappears from public /boka/.

    Step 1 treatment, step 2 one day's start times, step 3 name and phone.
    E-post is optional. Same treatment-plus-buffer rules as the public page.
    """
    services = Service.objects.filter(is_active=True)
    service_slug = request.POST.get("service") or request.GET.get("service")
    selected_service = None
    if service_slug:
        selected_service = get_object_or_404(Service, slug=service_slug, is_active=True)

    today = timezone.localdate()
    last_day = today + timedelta(days=PUBLIC_SLOT_HORIZON_DAYS)
    day = _parse_staff_day(request.POST.get("day") or request.GET.get("day"))
    day_slots = _bookable_on_day(selected_service, day) if selected_service else []

    slot_id = request.POST.get("slot") or request.GET.get("slot")
    selected_slot = None
    if slot_id and selected_service:
        selected_slot = TimeSlot.objects.filter(pk=slot_id).first()
        slot_day = (
            timezone.localtime(selected_slot.start).date() if selected_slot else None
        )
        if (
            selected_slot is None
            or slot_day != day
            or not can_start_service(selected_slot, selected_service)
        ):
            messages.error(
                request,
                "Den tiden räcker inte för behandlingen, eller är inte längre ledig.",
            )
            return redirect(_phone_day_url(selected_service, day))

    form = None
    booking_step = 1
    if selected_service and selected_slot:
        booking_step = 3
    elif selected_service:
        booking_step = 2

    if request.method == "POST" and selected_service and selected_slot:
        form = PhoneBookingForm(request.POST)
        if form.is_valid():
            try:
                booking = create_confirmed_booking(
                    service=selected_service,
                    start_slot=selected_slot,
                    customer_name=form.cleaned_data["customer_name"],
                    customer_email=form.cleaned_data["customer_email"],
                    customer_phone=form.cleaned_data["customer_phone"],
                    notify_email=form.cleaned_data["notify_email"],
                    notify_sms=False,
                    notes=form.cleaned_data.get("notes") or "",
                )
            except ValidationError:
                messages.error(request, "Den tiden just bokades av någon annan.")
                return redirect(_phone_day_url(selected_service, day))
            notify = send_booking_notifications(booking)
            when = timezone.localtime(booking.slot.start)
            messages.success(
                request,
                (
                    f"Bokat: {booking.customer_name}, {booking.service.name}, "
                    f"{when:%Y-%m-%d %H:%M}. Tiden syns inte längre på hemsidan."
                ),
            )
            if form.cleaned_data["notify_email"] and notify.get("email") is False:
                messages.warning(
                    request,
                    "Bokningen sparades men bekräftelsemejlet kunde inte skickas.",
                )
            return redirect(_phone_day_url(selected_service, day))
    elif selected_service and selected_slot:
        form = PhoneBookingForm()

    return render(
        request,
        "booking/dashboard_phone.html",
        {
            "services": services,
            "selected_service": selected_service,
            "selected_slot": selected_slot,
            "day": day,
            "today": today,
            "last_day": last_day,
            "prev_day": day - timedelta(days=1) if day > today else None,
            "next_day": day + timedelta(days=1) if day < last_day else None,
            "day_slots": day_slots,
            "form": form,
            "booking_step": booking_step,
        },
    )


@staff_member_required
def dashboard_help(request):
    """Swedish staff handbook — printable for the customer."""
    return render(request, "booking/dashboard_help.html")


def _slots_day_url(day):
    """Dashboard URL for one day's luckor."""
    return f"{reverse('dashboard_slots')}?day={day.isoformat()}"


def _validation_text(exc):
    """Swedish text from a ValidationError, including field errors."""
    if getattr(exc, "message_dict", None):
        parts = []
        for messages_for_field in exc.message_dict.values():
            parts.extend(messages_for_field)
        return " ".join(parts)
    return " ".join(getattr(exc, "messages", None) or [str(exc)])


def _cancel_posted_booking(request):
    """Cancel the booking id in POST. Returns the booking, or None when missing."""
    booking = (
        Booking.objects.filter(pk=request.POST.get("booking"))
        .select_related("slot", "service")
        .first()
    )
    if booking is None or booking.status != Booking.Status.CONFIRMED:
        messages.error(request, "Den bokningen finns inte kvar.")
        return None
    cancel_booking(booking)
    when = timezone.localtime(booking.slot.start)
    messages.success(
        request,
        (
            f"Avbokad: {booking.customer_name}, {when:%Y-%m-%d %H:%M}. "
            "Tiden är ledig på hemsidan igen."
        ),
    )
    return booking


def _slot_rows(day):
    """Luckor on this local day, with whether staff may cancel or delete each one."""
    start = timezone.make_aware(datetime.combine(day, time.min))
    end = start + timedelta(days=1)
    slots = list(
        TimeSlot.objects.filter(start__gte=start, start__lt=end)
        .select_related("held_by", "held_by__service", "held_by__slot")
        .order_by("start")
    )
    bookings = {
        booking.slot_id: booking
        for booking in Booking.objects.filter(slot__in=slots).select_related("service")
    }
    rows = []
    for slot in slots:
        booking = bookings.get(slot.pk)
        held = slot.held_by if slot.held_by_id else None
        confirmed = (
            booking
            if booking is not None and booking.status == Booking.Status.CONFIRMED
            else None
        )
        cancel_target = confirmed or (
            held if held is not None and held.status == Booking.Status.CONFIRMED else None
        )
        if confirmed:
            status = (
                f"Bokad: {confirmed.customer_name}, {confirmed.service.name}, "
                f"{confirmed.customer_phone}"
            )
        elif held:
            status = (
                f"Upptagen av {held.customer_name}, {held.service.name} "
                f"({timezone.localtime(held.slot.start):%H:%M})"
            )
        elif slot.is_blocked:
            status = "Blockerad"
        elif booking is not None:
            status = "Avbokad — luckan är ledig"
        else:
            status = "Ledig"
        rows.append(
            {
                "slot": slot,
                "status": status,
                "cancel_booking": cancel_target,
                "can_delete": confirmed is None and slot.held_by_id is None,
            }
        )
    return rows


@staff_member_required
@require_http_methods(["GET", "POST"])
def dashboard_slots(request):
    """Add or remove one lucka, and cancel the customer on a booked lucka.

    Removals are remembered so saving Veckoschema does not recreate them.
    Added luckor stay, and can be booked on Boka even outside opening hours.
    """
    today = timezone.localdate()
    last_day = today + timedelta(days=PUBLIC_SLOT_HORIZON_DAYS)
    day = _parse_staff_day(request.POST.get("day") or request.GET.get("day"))
    form = StaffSlotForm()

    if request.method == "POST":
        action = request.POST.get("action")
        if action == "cancel":
            _cancel_posted_booking(request)
            return redirect(_slots_day_url(day))
        if action == "delete":
            slot = TimeSlot.objects.filter(pk=request.POST.get("slot")).first()
            if slot is None or timezone.localtime(slot.start).date() != day:
                messages.error(request, "Den luckan finns inte den här dagen.")
            else:
                try:
                    when = timezone.localtime(slot.start)
                    remove_open_slot(slot)
                except ValidationError as exc:
                    messages.error(request, _validation_text(exc))
                else:
                    messages.success(
                        request,
                        (
                            f"Luckan {when:%H:%M} är borttagen. "
                            "Den syns inte på hemsidan och skapas inte igen."
                        ),
                    )
            return redirect(_slots_day_url(day))
        if action == "add":
            form = StaffSlotForm(request.POST)
            if form.is_valid():
                start = timezone.make_aware(datetime.combine(day, form.cleaned_data["start_time"]))
                end = timezone.make_aware(datetime.combine(day, form.cleaned_data["end_time"]))
                try:
                    add_staff_slot(start, end)
                except ValidationError as exc:
                    messages.error(request, _validation_text(exc))
                else:
                    messages.success(
                        request,
                        (
                            f"Luckan {start:%H:%M}–{end:%H:%M} är tillagd. "
                            "Den kan bokas på hemsidan."
                        ),
                    )
                    return redirect(_slots_day_url(day))
            for name in form.errors:
                if name in form.fields:
                    form.fields[name].widget.attrs["aria-invalid"] = "true"
                    form.fields[name].widget.attrs["aria-describedby"] = f"error_{name}"

    return render(
        request,
        "booking/dashboard_slots.html",
        {
            "day": day,
            "today": today,
            "last_day": last_day,
            "prev_day": day - timedelta(days=1) if day > today else None,
            "next_day": day + timedelta(days=1) if day < last_day else None,
            "rows": _slot_rows(day),
            "form": form,
        },
    )


@staff_member_required
@require_http_methods(["GET", "POST"])
def dashboard_home(request):
    """Staff landing page linking content admin and availability tools."""
    if request.method == "POST" and request.POST.get("action") == "cancel":
        _cancel_posted_booking(request)
        return redirect("dashboard")
    upcoming = (
        Booking.objects.filter(
            status=Booking.Status.CONFIRMED,
            slot__start__gte=timezone.now(),
        )
        .select_related("slot", "service")[:10]
    )
    open_count = (
        TimeSlot.objects.filter(
            start__gte=timezone.now(),
            is_blocked=False,
            held_by__isnull=True,
        )
        .exclude(booking__status=Booking.Status.CONFIRMED)
        .count()
    )
    return render(
        request,
        "booking/dashboard_home.html",
        {"upcoming": upcoming, "open_count": open_count},
    )


@staff_member_required
@require_http_methods(["GET", "POST"])
def dashboard_availability(request):
    """
    Staff UI to edit weekly hours and generate slots for a week or month.

    Weekly rules live in WeeklyAvailability; saving them syncs public Boka slots.
    """
    weekly = WeeklyAvailability.objects.all().order_by("weekday", "start_time")
    generate_form = AvailabilityGenerateForm(prefix="gen")
    week_form = QuickWeekForm(prefix="week")

    if request.method == "POST":
        action = request.POST.get("action")
        if action == "save_week":
            week_form = QuickWeekForm(request.POST, prefix="week")
            if week_form.is_valid():
                _save_quick_week(week_form.cleaned_data)
                created, deleted = sync_future_slots()
                messages.success(
                    request,
                    (
                        "Veckoschemat sparades. Boka är uppdaterad: "
                        f"{created} nya tider, {deleted} borttagna."
                    ),
                )
                return redirect("dashboard_availability")
        elif action == "generate":
            generate_form = AvailabilityGenerateForm(request.POST, prefix="gen")
            if generate_form.is_valid():
                start = generate_form.cleaned_data["start_date"]
                mode = generate_form.cleaned_data["mode"]
                if mode == "week":
                    end = start + timedelta(days=6)
                else:
                    last = monthrange(start.year, start.month)[1]
                    end = date(start.year, start.month, last)
                created, deleted = sync_slots_for_range(start, end)
                messages.success(
                    request,
                    f"Uppdaterade tidsluckor ({start} – {end}): {created} nya, {deleted} borttagna.",
                )
                return redirect("dashboard_availability")

    now = timezone.now()
    preview = (
        TimeSlot.objects.filter(start__gte=now, start__lte=now + timedelta(days=14))
        .order_by("start")[:40]
    )

    return render(
        request,
        "booking/dashboard_availability.html",
        {
            "weekly": weekly,
            "generate_form": generate_form,
            "week_form": week_form,
            "preview": preview,
            "weekday_labels": dict(WeeklyAvailability.WEEKDAYS),
        },
    )


def _save_quick_week(data):
    """Replace active weekly rules from the dashboard quick form."""
    WeeklyAvailability.objects.all().delete()
    slot_minutes = data["slot_minutes"]
    for weekday, label in WeeklyAvailability.WEEKDAYS:
        enabled = data.get(f"day_{weekday}_enabled")
        start = data.get(f"day_{weekday}_start")
        end = data.get(f"day_{weekday}_end")
        if enabled and start and end and start < end:
            WeeklyAvailability.objects.create(
                weekday=weekday,
                start_time=start,
                end_time=end,
                slot_minutes=slot_minutes,
                is_active=True,
                lunch_start=data.get(f"day_{weekday}_lunch_start") or None,
                lunch_end=data.get(f"day_{weekday}_lunch_end") or None,
            )
