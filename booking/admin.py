"""Admin for services, schedule, slots, and bookings."""

from django.contrib import admin

from .models import (
    PUBLIC_SLOT_HORIZON_DAYS,
    Booking,
    ClosedDate,
    Service,
    TimeSlot,
    WeeklyAvailability,
    sync_future_slots,
)


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


@admin.register(TimeSlot)
class TimeSlotAdmin(admin.ModelAdmin):
    list_display = ("start", "end", "is_blocked", "booked_display", "held_by")
    list_filter = ("is_blocked",)
    date_hierarchy = "start"
    actions = ["block_slots", "unblock_slots"]

    @admin.display(boolean=True, description="Bokad")
    def booked_display(self, obj):
        return Booking.objects.filter(slot=obj, status=Booking.Status.CONFIRMED).exists()

    @admin.action(description="Blockera valda luckor")
    def block_slots(self, request, queryset):
        queryset.update(is_blocked=True)

    @admin.action(description="Avblockera valda luckor")
    def unblock_slots(self, request, queryset):
        queryset.update(is_blocked=False)


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
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
