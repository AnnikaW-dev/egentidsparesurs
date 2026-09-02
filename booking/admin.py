"""Admin for services, schedule, slots, and bookings."""

from django.contrib import admin, messages
from django.core.exceptions import ValidationError
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.utils import timezone
from django.utils.html import format_html

from .forms import StaffBookingForm
from .models import (
    PUBLIC_SLOT_HORIZON_DAYS,
    Booking,
    ClosedDate,
    Service,
    TimeSlot,
    WeeklyAvailability,
    sync_future_slots,
    upcoming_open_slots,
)
from .notifications import send_booking_notifications


def _announce_boka_sync(admin_obj, request, created, deleted):
    """Tell staff that public /boka/ times were rebuilt from Veckoschema."""
    admin_obj.message_user(
        request,
        (
            f"Bokningsbara tider på Boka är uppdaterade "
            f"({PUBLIC_SLOT_HORIZON_DAYS} dagar framåt): "
            f"{created} nya, {deleted} borttagna. "
            "Befintliga kundbokningar är kvar."
        ),
    )


class ScheduleSyncAdminMixin:
    """After save/delete, rebuild public slots from the weekly schedule."""

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        created, deleted = sync_future_slots()
        _announce_boka_sync(self, request, created, deleted)

    def delete_model(self, request, obj):
        super().delete_model(request, obj)
        created, deleted = sync_future_slots()
        _announce_boka_sync(self, request, created, deleted)

    def delete_queryset(self, request, queryset):
        super().delete_queryset(request, queryset)
        created, deleted = sync_future_slots()
        _announce_boka_sync(self, request, created, deleted)


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ("name", "duration_minutes", "price_sek", "is_active", "sort_order")
    list_editable = ("is_active", "sort_order")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(WeeklyAvailability)
class WeeklyAvailabilityAdmin(ScheduleSyncAdminMixin, admin.ModelAdmin):
    """Edit Mon–Sun hours — footer Öppettider and public Boka slots."""

    list_display = (
        "weekday",
        "start_time",
        "end_time",
        "lunch_start",
        "lunch_end",
        "slot_minutes",
        "is_active",
    )
    list_editable = (
        "start_time",
        "end_time",
        "lunch_start",
        "lunch_end",
        "slot_minutes",
        "is_active",
    )
    list_display_links = ("weekday",)
    ordering = ("weekday", "start_time")
    list_filter = ("is_active", "weekday")
    fieldsets = (
        (
            None,
            {
                "fields": (
                    "weekday",
                    "start_time",
                    "end_time",
                    "lunch_start",
                    "lunch_end",
                    "is_active",
                    "slot_minutes",
                ),
                "description": (
                    "Dessa tider visas under Öppettider i sidfoten och blir "
                    "bokningsbara under Boka när du sparar. "
                    "Lägg till en rad per öppen dag (t.ex. Måndag 09:00–16:00). "
                    "Lunch från/till tar bort de luckorna från Boka den dagen "
                    "(lämna tomt om du inte tar lunch). "
                    "Dagar utan aktiv rad visas som ”Stängt” och går inte att boka. "
                    "Kundbokningar som redan finns tas inte bort."
                ),
            },
        ),
    )

    def changelist_view(self, request, extra_context=None):
        """List-editable save does not call save_model — sync after POST."""
        response = super().changelist_view(request, extra_context)
        if request.method == "POST" and "_save" in request.POST:
            created, deleted = sync_future_slots()
            _announce_boka_sync(self, request, created, deleted)
        return response


@admin.register(ClosedDate)
class ClosedDateAdmin(ScheduleSyncAdminMixin, admin.ModelAdmin):
    """A closed date removes that day's unbooked slots from Boka."""

    list_display = ("date", "reason")


class UpcomingSlotFilter(admin.SimpleListFilter):
    """Default the slot list to upcoming times so Boka kund is easy to find."""

    title = "När"
    parameter_name = "when"

    def lookups(self, request, model_admin):
        return (
            ("future", "Kommande"),
            ("all", "Alla"),
            ("past", "Passerade"),
        )

    def queryset(self, request, queryset):
        now = timezone.now()
        if self.value() == "all":
            return queryset
        if self.value() == "past":
            return queryset.filter(start__lt=now)
        return queryset.filter(start__gte=now)

    def choices(self, changelist):
        value = self.value() or "future"
        for lookup, title in self.lookup_choices:
            yield {
                "selected": value == str(lookup),
                "query_string": changelist.get_query_string(
                    {self.parameter_name: lookup}
                ),
                "display": title,
            }


@admin.register(TimeSlot)
class TimeSlotAdmin(admin.ModelAdmin):
    """Calendar slots; use Boka kund on an open row instead of editing raw fields."""

    list_display = (
        "start",
        "end",
        "is_blocked",
        "booked_display",
        "held_by",
        "book_customer",
    )
    list_filter = (UpcomingSlotFilter, "is_blocked")
    date_hierarchy = "start"
    actions = ["block_slots", "unblock_slots"]

    @admin.display(boolean=True, description="Bokad")
    def booked_display(self, obj):
        return Booking.objects.filter(slot=obj, status=Booking.Status.CONFIRMED).exists()

    @admin.display(description="Boka")
    def book_customer(self, obj):
        """Link to the staff booking form with this slot pre-selected."""
        if obj.held_by_id:
            return "Upptagen"
        if Booking.objects.filter(slot=obj, status=Booking.Status.CONFIRMED).exists():
            return "Bokad"
        if obj.is_blocked or obj.start <= timezone.now():
            return "—"
        url = reverse("admin:booking_booking_add") + f"?slot={obj.pk}"
        return format_html('<a href="{}">Boka kund</a>', url)

    @admin.action(description="Blockera valda luckor")
    def block_slots(self, request, queryset):
        queryset.update(is_blocked=True)

    @admin.action(description="Avblockera valda luckor")
    def unblock_slots(self, request, queryset):
        queryset.update(is_blocked=False)


def _release_held_slots(booking):
    """Free extra slots reserved after a treatment when the booking is cancelled."""
    TimeSlot.objects.filter(held_by=booking).update(held_by=None)


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    """List existing bookings; add form books a customer like public /boka/."""

    list_display = (
        "customer_name",
        "service",
        "slot",
        "customer_email",
        "customer_phone",
        "notify_email",
        "notify_sms",
        "status",
        "created_at",
    )
    list_filter = ("status", "service")
    search_fields = ("customer_name", "customer_email", "customer_phone")
    date_hierarchy = "created_at"
    save_on_top = True
    actions = ["cancel_bookings"]
    add_fieldsets = (
        (
            None,
            {
                "fields": (
                    "service",
                    "booking_date",
                    "booking_time",
                    "customer_name",
                    "customer_email",
                    "customer_phone",
                    "notify_email",
                    "notify_sms",
                    "notes",
                ),
                "description": (
                    "Boka in en kund som ringer eller kommer in. "
                    "Välj datum i kalendern och sedan klockslag. "
                    "Samma regler som på Boka: behandlingstiden plus 30 minuter reserveras. "
                    "Kunden får bekräftelse om e-post och/eller SMS är ikryssat. "
                    "Du kan också klicka på Boka kund under Tidsluckor."
                ),
            },
        ),
    )
    fieldsets = (
        (
            None,
            {
                "fields": (
                    "status",
                    "customer_name",
                    "customer_email",
                    "customer_phone",
                    "notify_email",
                    "notify_sms",
                    "notes",
                ),
            },
        ),
        (
            "Tid (ändras inte här — avboka och skapa en ny bokning i stället)",
            {"fields": ("service", "slot", "created_at")},
        ),
    )

    def get_fieldsets(self, request, obj=None):
        if obj is None:
            return self.add_fieldsets
        return super().get_fieldsets(request, obj)

    def get_form(self, request, obj=None, **kwargs):
        if obj is None:
            kwargs["form"] = StaffBookingForm
        return super().get_form(request, obj, **kwargs)

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        """Hide related-object plus/pencil icons — they confuse the booking form."""
        formfield = super().formfield_for_dbfield(db_field, request, **kwargs)
        if db_field.name in ("service", "slot") and formfield is not None:
            widget = formfield.widget
            for attr in (
                "can_add_related",
                "can_change_related",
                "can_delete_related",
                "can_view_related",
            ):
                if hasattr(widget, attr):
                    setattr(widget, attr, False)
        return formfield

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return ("service", "slot", "created_at")
        return ()

    def get_changeform_initial_data(self, request):
        """Pre-select a slot when arriving from Tidsluckor → Boka kund."""
        initial = super().get_changeform_initial_data(request)
        slot_id = request.GET.get("slot")
        if slot_id:
            initial["slot"] = slot_id
        return initial

    def add_view(self, request, form_url="", extra_context=None):
        """Use a clearer Swedish title than Django's default Lägg till bokning."""
        extra_context = extra_context or {}
        extra_context["title"] = "Boka in kund"
        if not upcoming_open_slots().exists():
            self.message_user(
                request,
                (
                    "Inga lediga tider att välja. Öppna Veckoschema / öppettider, "
                    "bocka i Aktiv för de dagar ni tar emot kunder, och spara. "
                    "Då skapas tider både här och på Boka."
                ),
                level=messages.WARNING,
            )
        return super().add_view(request, form_url, extra_context)

    def save_form(self, request, form, change):
        """On add, persist via StaffBookingForm (duration + buffer)."""
        if not change:
            return form.save()
        return super().save_form(request, form, change)

    def save_model(self, request, obj, form, change):
        """Send notices for new bookings; release extra slots when cancelled."""
        if not change:
            send_booking_notifications(obj)
            self.message_user(
                request,
                (
                    f"Bokningen är sparad: {obj.service.name} {obj.slot} "
                    f"för {obj.customer_name}. Behandling + 30 minuter är reserverade."
                ),
            )
            return
        previous_status = Booking.objects.get(pk=obj.pk).status
        super().save_model(request, obj, form, change)
        if obj.status == Booking.Status.CANCELLED and previous_status != Booking.Status.CANCELLED:
            _release_held_slots(obj)
            self.message_user(
                request,
                "Bokningen är avbokad. Tiderna är lediga på Boka igen.",
            )

    def changeform_view(self, request, object_id=None, form_url="", extra_context=None):
        """Show a Swedish error if the slot was taken between form load and save."""
        try:
            return super().changeform_view(request, object_id, form_url, extra_context)
        except ValidationError as exc:
            if object_id is None and request.method == "POST":
                self.message_user(
                    request,
                    " ".join(getattr(exc, "messages", None) or [str(exc)]),
                    level=messages.ERROR,
                )
                return HttpResponseRedirect(request.get_full_path())
            raise

    @admin.action(description="Avboka valda (frigör tiderna på Boka)")
    def cancel_bookings(self, request, queryset):
        """Mark confirmed bookings cancelled and free their held extra slots."""
        count = 0
        for booking in queryset.filter(status=Booking.Status.CONFIRMED):
            booking.status = Booking.Status.CANCELLED
            booking.save(update_fields=["status"])
            _release_held_slots(booking)
            count += 1
        self.message_user(
            request,
            f"{count} bokningar avbokade. Tiderna är lediga igen.",
        )
