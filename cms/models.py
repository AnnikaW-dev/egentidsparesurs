"""Editable site content: settings, pages, blocks, and gallery images."""

from django.db import models

from .text_format import BOLD_MARKUP_HINT, parse_body_sections


class SiteSettings(models.Model):
    """Singleton row for brand, contact, and footer text editable in admin."""

    site_name = models.CharField(max_length=120, default="EGentid Spa & Resurs")
    tagline = models.CharField(
        max_length=200,
        default="Skönhet & avkoppling – med en värmande touch!",
    )
    logo = models.ImageField(upload_to="brand/", blank=True)
    email = models.EmailField(blank=True, default="info@egentidsparesurs.se")
    phone = models.CharField(max_length=40, blank=True)
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
            "Fotvård, spa-pedikyr och värmande manikyr. Boka egentid hos EGentid Spa & Resurs."
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
    hero_image = models.ImageField(upload_to="pages/", blank=True)
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
        """Split body into non-empty paragraphs for templates."""
        return [p.strip() for p in self.body.split("\n\n") if p.strip()]

    def body_sections(self):
        """Parse ## / lists / paragraphs for richer CMS pages (e.g. Värmande)."""
        return parse_body_sections(self.body or "")

    def body_lines(self):
        """Split body into non-empty single lines (checklists)."""
        return [line.strip() for line in self.body.splitlines() if line.strip()]

    def seo_title(self):
        """Title used in <title> and Open Graph."""
        return (self.meta_title or self.title).strip()

    def seo_description(self, fallback=""):
        """Meta description: page override, else first body paragraph, else fallback."""
        if self.meta_description.strip():
            return self.meta_description.strip()
        paras = self.body_paragraphs()
        if paras:
            text = paras[0].replace("\n", " ")
            return text[:157] + ("…" if len(text) > 157 else "")
        return fallback


class ContentBlock(models.Model):
    """Optional titled section on a page (e.g. hand treatment highlight)."""

    page = models.ForeignKey(SitePage, on_delete=models.CASCADE, related_name="blocks")
    title = models.CharField(max_length=200)
    body = models.TextField(blank=True)
    image = models.ImageField(upload_to="blocks/", blank=True)
    sort_order = models.PositiveIntegerField(default=0)
    is_visible = models.BooleanField(default=True)

    class Meta:
        ordering = ["sort_order", "id"]
        verbose_name = "innehållsblock"
        verbose_name_plural = "innehållsblock"

    def __str__(self):
        return f"{self.page}: {self.title}"

    def body_paragraphs(self):
        return [p.strip() for p in self.body.split("\n\n") if p.strip()]

    def price_meta(self):
        """First paragraph when it looks like a price line (Prislista / Behandlingar)."""
        paras = self.body_paragraphs()
        if paras and "kr" in paras[0].lower():
            return paras[0]
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


class GalleryImage(models.Model):
    """Gallery photo editable from admin."""

    title = models.CharField(max_length=120, blank=True)
    image = models.ImageField(upload_to="gallery/")
    caption = models.CharField(max_length=255, blank=True)
    sort_order = models.PositiveIntegerField(default=0)
    is_visible = models.BooleanField(default=True)

    class Meta:
        ordering = ["sort_order", "id"]
        verbose_name = "galleribild"
        verbose_name_plural = "galleribilder"

    def __str__(self):
        return self.title or f"Bild {self.pk}"


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
    Startsidan shows the current month; Året runt lists all visible months.
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
