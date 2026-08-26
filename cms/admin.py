"""Admin registration for editable site content."""

from django.contrib import admin

from .models import (
    ContentBlock,
    GalleryImage,
    MonthHook,
    SeasonTip,
    SeasonTipItem,
    SitePage,
    SiteSettings,
)
from .text_format import BOLD_MARKUP_HINT


class ContentBlockInline(admin.TabularInline):
    model = ContentBlock
    extra = 1
    fields = ("title", "body", "image", "sort_order", "is_visible")
    verbose_name = "behandling / innehållsblock"
    verbose_name_plural = "behandlingar / innehållsblock"


class SeasonTipItemInline(admin.TabularInline):
    model = SeasonTipItem
    extra = 0
    fields = ("headline", "description", "sort_order")
    ordering = ("sort_order", "id")
    verbose_name = "äldre tipspunkt"
    verbose_name_plural = "äldre tipspunkter (används sällan – texten ligger i Brödtext)"
    classes = ("collapse",)


@admin.register(SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):
    fieldsets = (
        ("Varumärke", {"fields": ("site_name", "tagline", "logo")}),
        ("Kontakt", {"fields": ("email", "phone", "address")}),
        (
            "Öppettider i sidfot",
            {
                "fields": ("opening_hours",),
                "description": (
                    "Sidfoten visar inte längre veckoschema. "
                    "Där står i stället: ”Välkommen att boka tid under Boka” "
                    "(Boka är en länk). Fältet nedan används inte på sajten just nu."
                ),
                "classes": ("collapse",),
            },
        ),
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
        """Extra notes for Startsida and Behandlingar content blocks."""
        home_note = ""
        block_note = ""
        if obj and obj.key == SitePage.PageKey.HOME:
            home_note = (
                "Blocket ”Känner du igen det här?” under knapparna, och hela "
                "månadslistan på Året runt, redigeras under CMS → Känner du igen."
            )
        if obj and obj.key == SitePage.PageKey.TREATMENTS:
            block_note = (
                "Behandlingar redigeras som Innehållsblock nedan. "
                "Första raden i brödtext = pris (t.ex. 425 kr | ca 60 min). "
                "Använd ## för underrubrik, ✔ för checklista, tom rad mellan stycken. "
                + BOLD_MARKUP_HINT
                + " "
                "Ladda upp bild per block om du vill visa en bild ovanför texten."
            )
        content_description = " ".join(
            part
            for part in (
                home_note,
                block_note,
                BOLD_MARKUP_HINT,
            )
            if part
        )
        return (
            (None, {"fields": ("key", "title", "subtitle", "is_published")}),
            (
                "Innehåll",
                {
                    "fields": ("body", "hero_image"),
                    "description": content_description,
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
    list_display = ("month", "title", "is_visible")
    list_editable = ("is_visible",)
    list_filter = ("is_visible",)
    search_fields = ("title", "body")
    inlines = [SeasonTipItemInline]
    fieldsets = (
        (
            "Månad på Året runt",
            {
                "fields": ("month", "title", "icon", "is_visible"),
                "description": (
                    "Året runt visar automatiskt tipset för innevarande kalendermånad. "
                    "Öppna t.ex. Augusti för att redigera den text som syns i augusti."
                ),
            },
        ),
        (
            "Text på Året runt",
            {
                "fields": ("body",),
                "description": (
                    "Detta är den långa texten under månadsrubriken. "
                    "Använd ## för underrubrik och • eller ✔ för punktlista. "
                    + BOLD_MARKUP_HINT
                ),
            },
        ),
        (
            "Bild (valfritt)",
            {
                "fields": ("image",),
                "classes": ("collapse",),
            },
        ),
        (
            "Äldre avslutning (används sällan)",
            {
                "fields": (
                    "is_featured",
                    "closing_icon",
                    "closing_label",
                    "closing_body",
                    "closing_cta",
                ),
                "classes": ("collapse",),
                "description": (
                    "Äldre “Kort sagt”-rad och “featured”. Sidan styrs nu av "
                    "kalendermånad + brödtexten ovan."
                ),
            },
        ),
    )


@admin.register(MonthHook)
class MonthHookAdmin(admin.ModelAdmin):
    """Home recognition block — one entry per month under Boka/Se behandlingar."""

    list_display = ("month", "icon", "short_quote", "cta", "is_visible")
    list_editable = ("is_visible",)
    list_filter = ("is_visible",)
    search_fields = ("quote", "body", "cta")
    ordering = ("month",)
    fieldsets = (
        (
            None,
            {
                "fields": ("month", "icon", "is_visible"),
                "description": (
                    "Visas under Boka tid / Se behandlingar på startsidan "
                    "(innevarande månad). Året runt-texten redigeras under "
                    "CMS → Säsongstips."
                ),
            },
        ),
        (
            "Text",
            {
                "fields": ("quote", "body", "cta"),
                "description": (
                    "Citat visas i kursiv stil. CTA-raden länkar till bokningssidan. "
                    + BOLD_MARKUP_HINT
                ),
            },
        ),
    )

    @admin.display(description="Citat")
    def short_quote(self, obj):
        text = obj.quote or ""
        return text if len(text) <= 60 else f"{text[:57]}…"
