"""Public booking views and staff availability dashboard."""

from calendar import monthrange
from datetime import date, timedelta

from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from cms.models import SitePage

from .forms import AvailabilityGenerateForm, BookingForm, QuickWeekForm
from .models import (
    Booking,
    PUBLIC_SLOT_HORIZON_DAYS,
    Service,
    TimeSlot,
    WeeklyAvailability,
    create_confirmed_booking,
    slot_run_covering,
    sync_future_slots,
    sync_slots_for_range,
)
from .notifications import send_booking_notifications


def _booking_query(request):
    """Read selected service/slot from GET or POST."""
    service_slug = request.GET.get("service") or request.POST.get("service")
    slot_id = request.GET.get("slot") or request.POST.get("slot")
    return service_slug, slot_id


def booking_page(request):
    """Three-step booking: 1) treatment 2) time slot 3) name + phone."""
    page = SitePage.objects.filter(key=SitePage.PageKey.BOOKING, is_published=True).first()
    services = Service.objects.filter(is_active=True)
    service_slug, slot_id = _booking_query(request)

    selected_service = None
    if service_slug:
        selected_service = get_object_or_404(Service, slug=service_slug, is_active=True)

    selected_slot = None
    needed_minutes = None
    if slot_id and selected_service:
        selected_slot = get_object_or_404(TimeSlot, pk=slot_id)
        needed_minutes = selected_service.calendar_minutes()
        if not slot_run_covering(selected_slot, needed_minutes):
            messages.error(
                request,
                "Den tiden räcker inte för behandlingen, eller är inte längre ledig. Välj en annan lucka.",
            )
            return redirect(f"{request.path}?service={selected_service.slug}")

    now = timezone.now()
    horizon = now + timedelta(days=PUBLIC_SLOT_HORIZON_DAYS)
    open_slots = list(
        TimeSlot.objects.filter(
            start__gte=now,
            start__lte=horizon,
            is_blocked=False,
            held_by__isnull=True,
        )
        .exclude(booking__status=Booking.Status.CONFIRMED)
        .order_by("start")
    )
    open_by_start = {slot.start: slot for slot in open_slots}
    by_date = {}
    if selected_service:
        needed_minutes = selected_service.calendar_minutes()
        for slot in open_slots:
            if slot_run_covering(slot, needed_minutes, open_by_start=open_by_start):
                local = timezone.localtime(slot.start)
                by_date.setdefault(local.date(), []).append(slot)

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
                return redirect(f"{request.path}?service={selected_service.slug}")
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
