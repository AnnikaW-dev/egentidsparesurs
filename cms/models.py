"""Editable site content: settings, pages, blocks, and gallery images."""

from django.db import models
from django.utils import timezone

from .a11y import plain_cms_text, resolve_image_alt
from .text_format import BOLD_MARKUP_HINT, normalize_newlines, parse_body_sections


class SiteSettings(models.Model):
    """Singleton row for brand, contact, and footer text editable in admin."""

    site_name = models.CharField(max_length=120, default="EGentid Spa & Service")
    tagline = models.CharField(
        max_length=200,
        default="Skönhet & avkoppling – med en värmande touch!",
    )
    logo = models.ImageField(upload_to="brand/", blank=True)
    email = models.EmailField(
        blank=True,
        default="egentidspaservice@gmail.com",
        verbose_name="E-post",
        help_text=(
            "Visas i sidfoten. Kontaktformulär och nya bokningar skickas hit "
            "om CONTACT_INBOX inte är satt i miljön."
        ),
    )
    phone = models.CharField(
        max_length=40,
        blank=True,
        default="072-3170120",
        verbose_name="Telefonnummer",
        help_text="Visas i sidfoten under Kontakt. Lämna tomt för att dölja raden.",
    )
    address = models.TextField(blank=True, help_text=BOLD_MARKUP_HINT)
    opening_hours = models.TextField(
        blank=True,
        help_text=(
            "Används inte i sidfoten just nu. Sidfoten visar i stället "
            "”Välkommen att boka tid under Boka” med länk till bokning."
        ),
    )
    footer_text = models.TextField(
        blank=True,
        default="En lugn oas för fotvård, handvård och värmande behandlingar.",
        help_text=BOLD_MARKUP_HINT,
    )
    # Adjust: paste full profile URLs; leave blank to hide that icon in the footer.
    facebook_url = models.URLField(
        blank=True,
        help_text="Hela länken, t.ex. https://www.facebook.com/din-sida",
    )
    linkedin_url = models.URLField(
        blank=True,
        help_text="Hela länken, t.ex. https://www.linkedin.com/in/ditt-namn",
    )
    # SEO — Adjust: set production URL and default description in admin.
    public_site_url = models.URLField(
        blank=True,
        help_text="Publik bas-URL utan avslutande snedstreck, t.ex. https://egentidsparesurs.se",
    )
    default_meta_description = models.CharField(
        max_length=160,
        blank=True,
        default=(
            "Fotvård, spa-pedikyr och värmande manikyr. Boka egentid hos EGentid Spa & Service."
        ),
        help_text="Standard meta description (ca 150–160 tecken) om sidan saknar egen.",
    )
    og_image = models.ImageField(
        upload_to="seo/",
        blank=True,
        help_text="Delningsbild för sociala medier (valfritt). Annars används logotyp/hero.",
    )

    class Meta:
        verbose_name = "webbplatsinställningar"
        verbose_name_plural = "webbplatsinställningar"

    def __str__(self):
        return self.site_name

    def phone_tel(self) -> str:
        """Digits (and optional +) for tel: links; display text stays in phone."""
        raw = (self.phone or "").strip()
        if raw.startswith("+"):
            return "+" + "".join(ch for ch in raw[1:] if ch.isdigit())
        return "".join(ch for ch in raw if ch.isdigit())

    def save(self, *args, **kwargs):
        # Rule: only one settings row — always overwrite pk=1.
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def load(cls):
        """Return the singleton settings row, creating defaults if missing."""
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


class SitePage(models.Model):
    """A public page whose title, body, and hero image are editable in admin."""

    class PageKey(models.TextChoices):
        HOME = "home", "Startsida"
        SALON = "salon", "Om"
        TREATMENTS = "treatments", "Behandlingar & priser"
        WARMING = "warming", "Värmande behandlingar"
        PRICES = "prices", "Prislista"
        SEASONS = "seasons", "Året runt"
        GALLERY = "gallery", "Galleri"
        BOOKING = "booking", "Boka"
        CONTACT = "contact", "Kontakt"
        SERVICE = "service", "Service"

    key = models.CharField(max_length=32, choices=PageKey.choices, unique=True)
    title = models.CharField(max_length=200)
    subtitle = models.CharField(max_length=300, blank=True)
    body = models.TextField(
        blank=True,
        help_text=(
            "Huvudtext. Tom rad = nytt stycke. "
            "## underrubrik · • eller ✔ punktlista. "
            + BOLD_MARKUP_HINT
        ),
    )
    hero_image = models.ImageField(
        upload_to="pages/",
        blank=True,
        verbose_name="Egen hero-bild",
        help_text="Används om ingen bild är vald från Galleriet ovan.",
    )
    hero_gallery_image = models.ForeignKey(
        "GalleryImage",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="hero_pages",
        verbose_name="Hero från galleri",
        help_text=(
            "Välj en bild från Galleriet. Bildtexten från Galleribilder "
            "används som alt-text på sidan."
        ),
    )
    # Adjust: button labels on content pages (Värmande, Service, …); blank = template default
    cta_primary = models.CharField(
        max_length=120,
        blank=True,
        verbose_name="Huvudknapp",
        help_text="Text på huvudknappen (t.ex. Boka). Tom = sidans standardtext.",
    )
    cta_secondary = models.CharField(
        max_length=120,
        blank=True,
        verbose_name="Extraknapp",
        help_text=(
            "Text på den andra knappen (t.ex. Se värmande behandlingar & priser). "
            "Tom = ingen extraknapp (utom sidans inbyggda standard)."
        ),
    )
    # SEO overrides — leave blank to use title / default site description.
    meta_title = models.CharField(
        max_length=70,
        blank=True,
        help_text="Valfri SEO-titel (annars används sidans titel).",
    )
    meta_description = models.CharField(
        max_length=160,
        blank=True,
        help_text="Valfri meta description för denna sida.",
    )
    is_published = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["key"]
        verbose_name = "sida"
        verbose_name_plural = "sidor"

    def __str__(self):
        return self.get_key_display()

    def body_paragraphs(self):
        """Split body into non-empty paragraphs for templates.

        Admin on Windows saves CRLF; normalize so a blank line still starts a new paragraph.
        """
        text = normalize_newlines(self.body)
        return [p.strip() for p in text.split("\n\n") if p.strip()]

    def body_sections(self):
        """Parse ## / lists / paragraphs for richer CMS pages (e.g. Värmande)."""
        return parse_body_sections(self.body or "")

    def body_lines(self):
        """Split body into non-empty single lines (checklists)."""
        return [line.strip() for line in self.body.splitlines() if line.strip()]

    def seo_title(self):
        """Title used in <title> and Open Graph (legacy Resurs name rewritten)."""
        from cms.brand import with_current_brand

        return with_current_brand((self.meta_title or self.title).strip())

    def document_title(self, site_name: str = "") -> str:
        """Full browser tab title without duplicating the brand name."""
        from cms.brand import document_title as compose_document_title

        return compose_document_title(self.seo_title(), site_name)

    def seo_description(self, fallback=""):
        """Meta description: page override, else first body paragraph, else fallback."""
        from cms.brand import with_current_brand

        if self.meta_description.strip():
            return with_current_brand(self.meta_description.strip())
        paras = self.body_paragraphs()
        if paras:
            text = paras[0].replace("\n", " ")
            text = with_current_brand(text)
            return text[:157] + ("…" if len(text) > 157 else "")
        return with_current_brand(fallback)

    @property
    def resolved_hero_image(self):
        """Hero file: gallery pick first, else direct upload."""
        if self.hero_gallery_image_id:
            gallery = self.hero_gallery_image
            if gallery and gallery.image:
                return gallery.image
        return self.hero_image

    @property
    def resolved_hero_alt(self) -> str:
        """Alt text for hero: gallery caption → page title → default."""
        title_fallback = plain_cms_text(self.title)
        if self.hero_gallery_image_id and self.hero_gallery_image:
            return self.hero_gallery_image.alt_text(fallback=title_fallback)
        if self.hero_image:
            return resolve_image_alt(fallback=title_fallback)
        return ""

    def hero_carousel_items(self):
        """Hero photos for Hem / Behandlingar.

        One image → still photo. Two or more (page hero + extra slides) → carousel.
        Extra slides: Admin → Sidor → Hero-karusell.
        """
        items = []
        seen = set()

        def add(image, alt):
            if not image:
                return
            key = getattr(image, "name", None) or id(image)
            if not key or key in seen:
                return
            seen.add(key)
            items.append({"image": image, "alt": alt or ""})

        add(self.resolved_hero_image, self.resolved_hero_alt)
        for slide in self.hero_slides.all():
            add(slide.resolved_image, slide.resolved_alt(self.title))
        return items


class ContentBlock(models.Model):
    """Optional titled section on a page (e.g. hand treatment highlight)."""

    page = models.ForeignKey(SitePage, on_delete=models.CASCADE, related_name="blocks")
    title = models.CharField(max_length=200)
    body = models.TextField(blank=True)
    image = models.ImageField(
        upload_to="blocks/",
        blank=True,
        verbose_name="Egen bild",
        help_text="Används om ingen bild är vald från Galleriet ovan.",
    )
    gallery_image = models.ForeignKey(
        "GalleryImage",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="content_blocks",
        verbose_name="Bild från galleri",
        help_text=(
            "Välj en bild från Galleriet. Bildtexten från Galleribilder "
            "används som alt-text."
        ),
    )
    sort_order = models.PositiveIntegerField(default=0)
    is_visible = models.BooleanField(default=True)

    class Meta:
        ordering = ["sort_order", "id"]
        verbose_name = "innehållsblock"
        verbose_name_plural = "innehållsblock"

    def __str__(self):
        return f"{self.page}: {self.title}"

    def body_paragraphs(self):
        """Split body into paragraphs; CRLF from admin counts as a normal line break."""
        text = normalize_newlines(self.body)
        return [p.strip() for p in text.split("\n\n") if p.strip()]

    def price_meta(self):
        """First paragraph when it looks like a price line (Prislista / Behandlingar)."""
        paras = self.body_paragraphs()
        if paras and "kr" in paras[0].lower():
            # Match live WordPress look: 425 kr | ca 60 min
            return paras[0].replace(" · ", " | ").replace(" • ", " | ")
        return ""

    def body_sections(self):
        """Structured sections; skips leading price line when present."""
        body = self.body
        meta = self.price_meta()
        if meta:
            body = "\n\n".join(self.body_paragraphs()[1:])
        return parse_body_sections(body)

    def book_label(self):
        """CTA label for bookable treatments — Adjust: title before en-dash."""
        # Category headings on Behandlingar & priser (no book button)
        if self.title in {"Fötter", "Händer", "Massage"}:
            return ""
        if self.title.startswith("Olja ") or self.title.startswith("Varför "):
            return ""
        short = self.title.split(" – ")[0].split(" - ")[0].strip()
        return f"Boka {short}" if short else ""

    def is_category_heading(self):
        """True for Fötter / Händer / Massage section titles on treatments page."""
        return self.title in {"Fötter", "Händer", "Massage"}

    def shows_book_cta(self):
        return bool(self.book_label())

    def book_service_slug(self):
        """Slug for booking step 1 link — matches booking.Service by title."""
        from booking.models import Service

        service = Service.objects.filter(name=self.title, is_active=True).first()
        return service.slug if service else ""

    def body_lines(self):
        """Non-empty lines for checklist-style sections."""
        return [line.strip() for line in self.body.splitlines() if line.strip()]

    def price_label(self):
        """Last body line starting with ‘Pris:’ for prislista blocks, else empty."""
        for line in reversed(self.body_lines()):
            if line.lower().startswith("pris:"):
                return line
        return ""

    def price_body_lines(self):
        """Body lines excluding the trailing Pris: line (for bullets / copy)."""
        lines = self.body_lines()
        if lines and lines[-1].lower().startswith("pris:"):
            return lines[:-1]
        return lines

    def price_intro(self):
        """First non-bullet paragraph before checklist lines on a prislista item."""
        lines = self.price_body_lines()
        if not lines:
            return ""
        # Lines after a blank-separated intro are bullets; first chunk is intro.
        # Simpler: first line is intro if more follow, or whole text if one line.
        return lines[0]

    def price_bullets(self):
        """Checklist lines under a prislista item (everything after the intro)."""
        lines = self.price_body_lines()
        return lines[1:] if len(lines) > 1 else []

    @property
    def resolved_image(self):
        """Block image file: gallery pick first, else direct upload."""
        if self.gallery_image_id:
            gallery = self.gallery_image
            if gallery and gallery.image:
                return gallery.image
        return self.image

    @property
    def resolved_image_alt(self) -> str:
        """Alt text: gallery caption → block title → default."""
        title_fallback = plain_cms_text(self.title)
        if self.gallery_image_id and self.gallery_image:
            return self.gallery_image.alt_text(fallback=title_fallback)
        if self.image:
            return resolve_image_alt(fallback=title_fallback)
        return ""


class GalleryImage(models.Model):
    """Gallery photo editable from admin."""

    title = models.CharField(max_length=120, blank=True)
    image = models.ImageField(upload_to="gallery/")
    caption = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="Bildtext (alt-text)",
        help_text=(
            "Kort beskrivning för skärmläsare. Används på Galleri och när bilden "
            "väljes på sidor/block. Tom = titeln används."
        ),
    )
    sort_order = models.PositiveIntegerField(default=0)
    is_visible = models.BooleanField(default=True)

    class Meta:
        ordering = ["sort_order", "id"]
        verbose_name = "galleribild"
        verbose_name_plural = "galleribilder"

    def __str__(self):
        return self.title or f"Bild {self.pk}"

    def alt_text(self, fallback: str = "") -> str:
        """Alt text for this image wherever it is reused (gallery, hero, blocks)."""
        return resolve_image_alt(
            caption=self.caption,
            title=self.title,
            fallback=fallback,
        )

    def missing_alt_warning(self) -> bool:
        """True when visible image lacks both caption and title (admin reminder)."""
        return self.is_visible and not plain_cms_text(self.caption) and not plain_cms_text(
            self.title
        )


class PageHeroSlide(models.Model):
    """Extra hero photo on a page. Two or more images become a carousel."""

    page = models.ForeignKey(
        SitePage,
        on_delete=models.CASCADE,
        related_name="hero_slides",
    )
    gallery_image = models.ForeignKey(
        GalleryImage,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="page_hero_slides",
        verbose_name="Bild från galleri",
        help_text="Välj från Galleribilder. Bildtexten används som alt-text.",
    )
    image = models.ImageField(
        upload_to="heroes/",
        blank=True,
        verbose_name="Egen bild",
        help_text="Används om ingen bild är vald från Galleriet.",
    )
    sort_order = models.PositiveIntegerField(default=0, verbose_name="Ordning")

    class Meta:
        ordering = ["sort_order", "id"]
        verbose_name = "extra hero-bild"
        verbose_name_plural = "hero-karusell (fler än en bild = bildspel)"

    def __str__(self):
        return f"{self.page}: hero {self.sort_order}"

    @property
    def resolved_image(self):
        """Gallery pick first, else uploaded file."""
        if self.gallery_image_id:
            gallery = self.gallery_image
            if gallery and gallery.image:
                return gallery.image
        return self.image

    def resolved_alt(self, page_title: str = "") -> str:
        """Alt text: gallery caption → page title → default."""
        title_fallback = plain_cms_text(page_title)
        if self.gallery_image_id and self.gallery_image:
            return self.gallery_image.alt_text(fallback=title_fallback)
        if self.image:
            return resolve_image_alt(fallback=title_fallback)
        return resolve_image_alt(fallback=title_fallback)


class SeasonTip(models.Model):
    """One month’s tip block on Året runt. Mark one as featured to show on the site."""

    MONTH_CHOICES = [
        (1, "Januari"),
        (2, "Februari"),
        (3, "Mars"),
        (4, "April"),
        (5, "Maj"),
        (6, "Juni"),
        (7, "Juli"),
        (8, "Augusti"),
        (9, "September"),
        (10, "Oktober"),
        (11, "November"),
        (12, "December"),
    ]

    month = models.PositiveSmallIntegerField(
        choices=MONTH_CHOICES,
        unique=True,
        help_text="Vilken kalendermånad tipset hör till.",
    )
    # Adjust: full heading shown under the intro, e.g. “Mars – Vårens första månad”
    title = models.CharField(
        max_length=200,
        help_text="Rubrik under introtexten, t.ex. Mars – Vårens första månad",
    )
    # Adjust: emoji shown left of the month heading (🌱 in the WordPress layout)
    icon = models.CharField(
        max_length=8,
        default="🌱",
        blank=True,
        help_text="Emoji eller symbol framför månadsrubriken.",
    )
    body = models.TextField(
        blank=True,
        help_text=(
            "Huvudtexten på Året runt för denna månad. "
            "## = underrubrik, • eller ✔ = punktlista. " + BOLD_MARKUP_HINT
        ),
    )
    # Adjust: “Kort sagt …” line under the checklist (see WordPress month tips)
    closing_icon = models.CharField(
        max_length=8,
        default="💡",
        blank=True,
        help_text="Emoji framför avslutningen, t.ex. 💡",
    )
    closing_label = models.CharField(
        max_length=40,
        default="Kort sagt:",
        blank=True,
        help_text="Fet stil i början, t.ex. Kort sagt:",
    )
    closing_body = models.CharField(
        max_length=300,
        blank=True,
        help_text="Text efter etiketten, före bokningslänken.",
    )
    closing_cta = models.CharField(
        max_length=80,
        default="boka din behandling nu!",
        blank=True,
        help_text="Fet länkad text till Boka-sidan. Tom = ingen länk.",
    )
    image = models.ImageField(upload_to="seasons/", blank=True)
    is_featured = models.BooleanField(
        default=False,
        verbose_name="Visas på Året runt (äldre)",
        help_text=(
            "Används inte längre. Året runt visar automatiskt innevarande "
            "kalendermånad utifrån fältet Månad."
        ),
    )
    is_visible = models.BooleanField(default=True)

    class Meta:
        ordering = ["month"]
        verbose_name = "säsongstips"
        verbose_name_plural = "säsongstips"

    def __str__(self):
        return self.title

    def body_sections(self):
        """Parse body for home “Månadens tips” (## / ✔ / paragraphs)."""
        return parse_body_sections(self.body or "")

    def body_intro_sections(self):
        """First paragraph on Året runt — shown before Läs mer."""
        sections = self.body_sections()
        if sections and sections[0]["type"] == "para":
            return [sections[0]]
        return []

    def body_rest_sections(self):
        """Remaining body after the intro paragraph."""
        sections = self.body_sections()
        if sections and sections[0]["type"] == "para":
            return sections[1:]
        return sections

    def has_collapsible_content(self):
        """True when Året runt should offer Läs mer (body rest, items, or closing)."""
        return bool(
            self.body_rest_sections()
            or self.items.exists()
            or self.closing_label
            or self.closing_body
            or self.closing_cta
        )

    @classmethod
    def rolling_display_months(cls, from_date=None):
        """Months shown on Året runt: current calendar month plus the next two."""
        if from_date is None:
            from_date = timezone.localdate()
        start = from_date.month
        return [((start + offset - 1) % 12) + 1 for offset in range(3)]

    @classmethod
    def month_label(cls, month):
        """Swedish month name for a month number (1–12)."""
        return dict(cls.MONTH_CHOICES).get(month, "")

    @classmethod
    def tips_for_rolling_window(cls, from_date=None):
        """Visible tips for current month + next two, in display order."""
        months = cls.rolling_display_months(from_date)
        tips = {
            tip.month: tip
            for tip in cls.objects.filter(month__in=months, is_visible=True).prefetch_related(
                "items"
            )
        }
        return [
            {
                "month": month,
                "month_label": cls.month_label(month),
                "tip": tips.get(month),
                "heading_id": f"season-tip-{month}",
            }
            for month in months
        ]

    def save(self, *args, **kwargs):
        # Rule: at most one featured tip — clearing others when this one is featured.
        super().save(*args, **kwargs)
        if self.is_featured:
            SeasonTip.objects.filter(is_featured=True).exclude(pk=self.pk).update(
                is_featured=False
            )


class SeasonTipItem(models.Model):
    """Checklist row under a month tip: bold headline + explanation."""

    tip = models.ForeignKey(
        SeasonTip,
        on_delete=models.CASCADE,
        related_name="items",
    )
    # Adjust: bold part before the dash on Året runt
    headline = models.CharField(max_length=200)
    description = models.CharField(max_length=300)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "id"]
        verbose_name = "tipspunkt"
        verbose_name_plural = "tipspunkter"

    def __str__(self):
        return self.headline


class MonthHook(models.Model):
    """Home “Känner du igen det här?” — one quote block per calendar month.

    Edit in Admin → CMS → Känner du igen.
    Startsidan shows the current month only.
    """

    MONTH_CHOICES = SeasonTip.MONTH_CHOICES

    month = models.PositiveSmallIntegerField(
        choices=MONTH_CHOICES,
        unique=True,
        help_text="Vilken kalendermånad blocket hör till.",
    )
    # Adjust: emoji before month name on startsidan
    icon = models.CharField(
        max_length=8,
        blank=True,
        default="",
        help_text="Emoji framför månadsnamnet, t.ex. 🌾",
    )
    quote = models.CharField(
        max_length=300,
        help_text=(
            "Citatet i kursiv stil (utan citationstecken — de läggs till i mallen). "
            + BOLD_MARKUP_HINT
        ),
    )
    body = models.TextField(
        help_text="Stödtext under citatet. " + BOLD_MARKUP_HINT,
    )
    cta = models.CharField(
        max_length=200,
        help_text=(
            "Länktext under texten (går till Boka), t.ex. Återhämtande fotvård. "
            + BOLD_MARKUP_HINT
        ),
    )
    is_visible = models.BooleanField(
        default=True,
        help_text="Avmarkera för att dölja denna månad på startsidan.",
    )

    class Meta:
        ordering = ["month"]
        verbose_name = "känner du igen"
        verbose_name_plural = "känner du igen"

    def __str__(self):
        return f"{self.get_month_display()} – {self.quote[:40]}"
