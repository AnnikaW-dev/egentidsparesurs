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

    def get_fieldsets(self, request, obj=None):
        """Extra note on Startsida: monthly tip is edited under Säsongstips."""
        home_note = ""
        if obj and obj.key == SitePage.PageKey.HOME:
            home_note = (
                "Månadens tips under knapparna på startsidan redigeras inte här. "
                "Gå till CMS → Säsongstips och öppna raden för rätt månad "
                "(sajten visar automatiskt innevarande månad)."
            )
        return (
            (None, {"fields": ("key", "title", "subtitle", "is_published")}),
            (
                "Innehåll",
                {
                    "fields": ("body", "hero_image"),
                    "description": home_note,
                },
            ),
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
    """One tip per calendar month — home page shows the current month automatically."""

    list_display = ("month", "title", "is_visible")
    list_editable = ("is_visible",)
    ordering = ("month",)
    list_display_links = ("month", "title")
    fieldsets = (
        (
            None,
            {
                "fields": ("month", "title", "body", "image", "is_visible"),
                "description": (
                    "Startsida visar automatiskt tipset för innevarande månad "
                    "(t.ex. i september → öppna September). "
                    "I brödtexten: ## för underrubrik, ✔ för checklista, tom rad mellan stycken."
                ),
            },
        ),
    )
