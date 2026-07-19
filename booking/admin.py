"""Admin for services, schedule, slots, and bookings."""

from django.contrib import admin

from .models import (
    Booking,
    ClosedDate,
    Service,
    TimeSlot,
    WeeklyAvailability,
)


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ("name", "duration_minutes", "price_sek", "is_active", "sort_order")
    list_editable = ("is_active", "sort_order")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(WeeklyAvailability)
class WeeklyAvailabilityAdmin(admin.ModelAdmin):
    """Edit Mon–Sun hours — shown under Öppettider in the footer and used for Boka."""

    list_display = ("weekday", "start_time", "end_time", "slot_minutes", "is_active")
    list_editable = ("start_time", "end_time", "slot_minutes", "is_active")
    list_display_links = ("weekday",)
    ordering = ("weekday", "start_time")
    list_filter = ("is_active", "weekday")
    fieldsets = (
        (
            None,
            {
                "fields": ("weekday", "start_time", "end_time", "is_active", "slot_minutes"),
                "description": (
                    "Dessa tider visas under Öppettider i sidfoten. "
                    "Lägg till en rad per öppen dag (t.ex. Måndag 09:00–16:00). "
                    "Dagar utan aktiv rad visas som ”Stängt”. "
                    "Du kan också ändra schemat under /dashboard/."
                ),
            },
        ),
    )


@admin.register(ClosedDate)
class ClosedDateAdmin(admin.ModelAdmin):
    list_display = ("date", "reason")


@admin.register(TimeSlot)
class TimeSlotAdmin(admin.ModelAdmin):
    list_display = ("start", "end", "is_blocked", "booked_display")
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
        "status",
        "created_at",
    )
    list_filter = ("status", "service")
    search_fields = ("customer_name", "customer_email", "customer_phone")
    date_hierarchy = "created_at"
