"""Admin registration for editable site content."""

from django.contrib import admin, messages

from .a11y import A11Y_BLOCK_IMAGE_HELP, A11Y_GALLERY_CAPTION_HELP, A11Y_PAGE_IMAGE_HELP
from .models import (
    ContentBlock,
    GalleryImage,
    MonthHook,
    PageHeroSlide,
    SeasonTip,
    SeasonTipItem,
    SitePage,
    SiteSettings,
)
from .text_format import BOLD_MARKUP_HINT


class PageHeroSlideInline(admin.TabularInline):
    model = PageHeroSlide
    extra = 1
    fields = ("gallery_image", "image", "sort_order")
    autocomplete_fields = ("gallery_image",)
    verbose_name = "extra hero-bild"
    verbose_name_plural = (
        "Hero-karusell — lägg till fler bilder för bildspel på Hem och Behandlingar "
        "(en bild = stilla hero)"
    )


class ContentBlockInline(admin.TabularInline):
    model = ContentBlock
    extra = 1
    fields = ("title", "body", "gallery_image", "image", "sort_order", "is_visible")
    autocomplete_fields = ("gallery_image",)
    verbose_name = "behandling / innehållsblock"
    verbose_name_plural = "behandlingar / innehållsblock (bildtext följer från Galleriet)"


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
        ("Kontakt", {"fields": ("email", "phone", "address"), "description": "E-post och telefonnummer visas i sidfoten."}),
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
    autocomplete_fields = ("hero_gallery_image",)
    inlines = [ContentBlockInline]

    def get_inlines(self, request, obj=None):
        """Hero carousel only on Hem and Behandlingar — other pages keep a single hero."""
        if obj and obj.key in (SitePage.PageKey.HOME, SitePage.PageKey.TREATMENTS):
            return [PageHeroSlideInline, ContentBlockInline]
        return [ContentBlockInline]

    def get_fieldsets(self, request, obj=None):
        """Extra notes for Startsida, Behandlingar and Värmande."""
        home_note = ""
        block_note = ""
        if obj and obj.key == SitePage.PageKey.HOME:
            home_note = (
                "Hero: en bild = stilla. Fler rader under Hero-karusell = bildspel. "
                "Blocket ”Känner du igen det här?” under knapparna, och hela "
                "månadslistan på Året runt, redigeras under CMS → Känner du igen."
            )
        if obj and obj.key == SitePage.PageKey.TREATMENTS:
            block_note = (
                "Hero: en bild = stilla. Fler rader under Hero-karusell = bildspel. "
                "Behandlingar redigeras som Innehållsblock nedan. "
                "Första raden i brödtext = pris (t.ex. 425 kr | ca 60 min). "
                "Använd ## för underrubrik, ✔ för checklista, tom rad mellan stycken. "
                + BOLD_MARKUP_HINT
                + " "
                "Ladda upp bild per block om du vill visa en bild ovanför texten. "
                "Eller välj Bild från galleri i innehållsblocket (samma bilder som under Galleribilder). "
                + A11Y_BLOCK_IMAGE_HELP
            )
        if obj and obj.key == SitePage.PageKey.WARMING:
            block_note = (
                "All text på sidan redigeras här: titel, underrubrik och brödtext. "
                "Brödtext: ## underrubrik, • punktlista, tom rad mellan stycken. "
                + BOLD_MARKUP_HINT
                + " "
                "Extraknappen går till Behandlingar & priser; huvudknappen till Boka. "
                "Välj hero eller bilder från Galleriet (Hero från galleri / Bild från galleri). "
                "Ändringar sparas direkt — seed skriver inte över dem."
            )
        if obj and obj.key == SitePage.PageKey.SALON:
            block_note = (
                "Innehållsblocket visas under Boka-knappen: välj porträtt från Galleriet "
                "eller ladda upp bild. Bildtext = alt-text för skärmläsare. "
                + BOLD_MARKUP_HINT
                + " "
                + A11Y_BLOCK_IMAGE_HELP
            )
        if obj and obj.key == SitePage.PageKey.SERVICE:
            block_note = (
                "Underrubrik och brödtext stödjer **fet stil**. "
                "Knappen går till kontaktformuläret. "
                + BOLD_MARKUP_HINT
            )
        content_description = " ".join(
            part
            for part in (
                home_note,
                block_note,
                BOLD_MARKUP_HINT,
                A11Y_PAGE_IMAGE_HELP,
            )
            if part
        )
        fieldsets = [
            (None, {"fields": ("key", "title", "subtitle", "is_published")}),
            (
                "Innehåll",
                {
                    "fields": ("body", "hero_gallery_image", "hero_image"),
                    "description": content_description,
                },
            ),
            (
                "Knappar",
                {
                    "fields": ("cta_secondary", "cta_primary"),
                    "description": (
                        "Extraknapp = länk till Behandlingar & priser (Värmande). "
                        "Huvudknapp = Boka (eller Kontaktformulär på Service). "
                        "Tomt fält = sidans standardtext."
                    ),
                },
            ),
            (
                "SEO",
                {
                    "fields": ("meta_title", "meta_description"),
                    "description": "Valfritt. Tomt = sidans titel / standardbeskrivning.",
                },
            ),
        ]
        return fieldsets


@admin.register(GalleryImage)
class GalleryImageAdmin(admin.ModelAdmin):
    list_display = ("title", "caption", "alt_status", "sort_order", "is_visible")
    list_editable = ("sort_order", "is_visible")
    search_fields = ("title", "caption")
    fieldsets = (
        (
            None,
            {
                "fields": ("title", "image", "caption", "sort_order", "is_visible"),
                "description": A11Y_GALLERY_CAPTION_HELP,
            },
        ),
    )

    @admin.display(description="Bildtext OK")
    def alt_status(self, obj):
        if obj.missing_alt_warning():
            return "Saknas"
        return "OK"

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        if obj.missing_alt_warning():
            messages.warning(
                request,
                f"Galleribild ”{obj}” saknar titel och bildtext. "
                "Lägg till en kort bildtext så skärmläsare förstår bilden (WCAG).",
            )


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
                    "Året runt visar automatiskt innevarande månad plus de två nästkommande. "
                    "Första stycket i brödtext syns direkt; resten bakom Läs mer. "
                    "Redigera en rad per kalendermånad."
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
