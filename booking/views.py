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

from .forms import AvailabilityGenerateForm, BookingForm, PhoneBookingForm, QuickWeekForm
from .models import (
    PUBLIC_SLOT_HORIZON_DAYS,
    Booking,
    Service,
    TimeSlot,
    WeeklyAvailability,
    bookable_start_slots,
    can_start_service,
    create_confirmed_booking,
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


@staff_member_required
def dashboard_home(request):
    """Staff landing page linking content admin and availability tools."""
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
