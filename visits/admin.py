# visits/admin.py — read-only Besöksstatistik with today / 7 / 30 / total

from django.contrib import admin

from .models import SiteTrafficDay
from .tracking import traffic_summary


@admin.register(SiteTrafficDay)
class SiteTrafficDayAdmin(admin.ModelAdmin):
    """Daily rows plus the summary table. Counts are written only by tracking."""

    change_list_template = "admin/visits/sitetrafficday/change_list.html"
    list_display = ("day", "unique_visitors", "pageviews")
    date_hierarchy = "day"
    ordering = ("-day",)
    list_per_page = 31

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context["traffic_summary"] = traffic_summary()
        return super().changelist_view(request, extra_context=extra_context)
