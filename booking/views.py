"""Public booking views and staff availability dashboard."""

from calendar import monthrange
from datetime import date, timedelta

from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from cms.models import SitePage

from .forms import AvailabilityGenerateForm, BookingForm, QuickWeekForm
from .models import Booking, Service, TimeSlot, WeeklyAvailability, generate_slots_for_range


def booking_page(request):
    """Show open slots and accept a booking for a selected slot."""
    page = SitePage.objects.filter(key=SitePage.PageKey.BOOKING, is_published=True).first()
    services = Service.objects.filter(is_active=True)
    now = timezone.now()
    horizon = now + timedelta(days=60)

    open_slots = (
        TimeSlot.objects.filter(start__gte=now, start__lte=horizon, is_blocked=False)
        .exclude(booking__status=Booking.Status.CONFIRMED)
        .order_by("start")
    )

    # Group by local date for the template calendar feel.
    by_date = {}
    for slot in open_slots:
        local = timezone.localtime(slot.start)
        by_date.setdefault(local.date(), []).append(slot)

    form = None
    selected_slot = None
    slot_id = request.GET.get("slot") or request.POST.get("slot")
    if slot_id:
        selected_slot = get_object_or_404(TimeSlot, pk=slot_id)
        if not selected_slot.is_open:
            messages.error(request, "Den tiden är inte längre ledig. Välj en annan lucka.")
            return redirect("booking")

    if request.method == "POST" and selected_slot:
        form = BookingForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                slot = TimeSlot.objects.select_for_update().get(pk=selected_slot.pk)
                if not slot.is_open:
                    messages.error(request, "Den tiden just bokades av någon annan.")
                    return redirect("booking")
                booking = form.save(commit=False)
                booking.slot = slot
                booking.status = Booking.Status.CONFIRMED
                booking.save()
            messages.success(
                request,
                f"Tack {booking.customer_name}! Din tid {timezone.localtime(slot.start):%Y-%m-%d %H:%M} är bokad.",
            )
            return redirect("booking_success", pk=booking.pk)
    elif selected_slot:
        form = BookingForm()

    return render(
        request,
        "booking/book.html",
        {
            "page": page,
            "services": services,
            "slots_by_date": sorted(by_date.items()),
            "form": form,
            "selected_slot": selected_slot,
        },
    )


def booking_success(request, pk):
    """Confirmation page after a successful booking."""
    booking = get_object_or_404(Booking, pk=pk)
    return render(request, "booking/success.html", {"booking": booking})


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
        TimeSlot.objects.filter(start__gte=timezone.now(), is_blocked=False)
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

    Weekly rules live in WeeklyAvailability; generate_slots_for_range materializes them.
    """
    weekly = WeeklyAvailability.objects.all().order_by("weekday", "start_time")
    generate_form = AvailabilityGenerateForm(prefix="gen")
    week_form = QuickWeekForm(prefix="week")
    created = None

    if request.method == "POST":
        action = request.POST.get("action")
        if action == "save_week":
            week_form = QuickWeekForm(request.POST, prefix="week")
            if week_form.is_valid():
                _save_quick_week(week_form.cleaned_data)
                messages.success(request, "Veckoschemat sparades.")
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
                    # If start is mid-month, still fill through month end.
                created = generate_slots_for_range(start, end)
                messages.success(
                    request,
                    f"Skapade {created} nya tidsluckor ({start} – {end}).",
                )
                return redirect("dashboard_availability")

    # Preview next 14 days of open slots
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
            )
