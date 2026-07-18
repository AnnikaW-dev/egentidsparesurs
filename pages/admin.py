"""Admin for contact messages."""

from django.contrib import admin

from .models import ContactMessage


@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ("name", "email", "subject", "status", "created_at")
    list_filter = ("status",)
    search_fields = ("name", "email", "subject", "message")
    readonly_fields = ("created_at",)
    list_editable = ("status",)
