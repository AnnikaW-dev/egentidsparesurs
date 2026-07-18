"""Admin registration for editable site content."""

from django.contrib import admin

from .models import ContentBlock, GalleryImage, SeasonTip, SitePage, SiteSettings


class ContentBlockInline(admin.TabularInline):
    model = ContentBlock
    extra = 1
    fields = ("title", "body", "image", "sort_order", "is_visible")


@admin.register(SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):
    fieldsets = (
        ("Varumärke", {"fields": ("site_name", "tagline", "logo")}),
        ("Kontakt", {"fields": ("email", "phone", "address", "opening_hours")}),
        (
            "Sidfot",
            {
                "fields": ("footer_text", "facebook_url", "linkedin_url"),
                "description": "Sociala länkar visas som ikoner i sidfoten. Tomt fält = dold ikon.",
            },
        ),
        (
            "SEO",
            {
                "fields": ("public_site_url", "default_meta_description", "og_image"),
                "description": "Sökmotorer och delning. Sätt publik URL när sajten är live.",
            },
        ),
    )

    def has_add_permission(self, request):
        return not SiteSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(SitePage)
class SitePageAdmin(admin.ModelAdmin):
    list_display = ("title", "key", "is_published", "updated_at")
    list_filter = ("is_published",)
    search_fields = ("title", "body", "meta_title", "meta_description")
    inlines = [ContentBlockInline]
    fieldsets = (
        (None, {"fields": ("key", "title", "subtitle", "is_published")}),
        ("Innehåll", {"fields": ("body", "hero_image")}),
        (
            "SEO",
            {
                "fields": ("meta_title", "meta_description"),
                "description": "Valfritt. Tomt = sidans titel / standardbeskrivning.",
            },
        ),
    )


@admin.register(GalleryImage)
class GalleryImageAdmin(admin.ModelAdmin):
    list_display = ("title", "sort_order", "is_visible")
    list_editable = ("sort_order", "is_visible")


@admin.register(SeasonTip)
class SeasonTipAdmin(admin.ModelAdmin):
    list_display = ("month", "title", "is_visible")
    list_editable = ("is_visible",)
