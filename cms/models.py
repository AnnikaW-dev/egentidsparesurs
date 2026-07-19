"""Editable site content: settings, pages, blocks, and gallery images."""

from django.db import models


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
    address = models.TextField(blank=True)
    opening_hours = models.TextField(
        blank=True,
        help_text=(
            "Valfri extratext under veckoschemat i sidfoten "
            "(t.ex. ”Bokning krävs”). Själva tiderna kommer från Veckoschema."
        ),
    )
    footer_text = models.TextField(
        blank=True,
        default="En lugn oas för fotvård, handvård och värmande behandlingar.",
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
        SALON = "salon", "Salongen"
        TREATMENTS = "treatments", "Behandlingar"
        SEASONS = "seasons", "Året runt"
        GALLERY = "gallery", "Galleri"
        BOOKING = "booking", "Boka"
        CONTACT = "contact", "Kontakt"

    key = models.CharField(max_length=32, choices=PageKey.choices, unique=True)
    title = models.CharField(max_length=200)
    subtitle = models.CharField(max_length=300, blank=True)
    body = models.TextField(
        blank=True,
        help_text="Huvudtext. Använd tom rad för nytt stycke.",
    )
    hero_image = models.ImageField(upload_to="pages/", blank=True)
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

    def body_lines(self):
        """Non-empty lines for checklist-style sections."""
        return [line.strip() for line in self.body.splitlines() if line.strip()]


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
        help_text="Valfri brödtext ovanför tipspunkterna.",
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
        verbose_name="Visas på Året runt",
        help_text="Visa detta tipset på Året runt-sidan. Endast ett kan vara valt.",
    )
    is_visible = models.BooleanField(default=True)

    class Meta:
        ordering = ["month"]
        verbose_name = "säsongstips"
        verbose_name_plural = "säsongstips"

    def __str__(self):
        return self.title

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
