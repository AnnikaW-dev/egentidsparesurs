"""Seed default pages, services, schedule, and copy from the WordPress site."""

from datetime import date, time, timedelta
from pathlib import Path

from django.core.files import File
from django.core.management.base import BaseCommand
from django.utils.text import slugify

from booking.models import Service, WeeklyAvailability, generate_slots_for_range
from cms.models import (
    ContentBlock,
    GalleryImage,
    MonthHook,
    SeasonTip,
    SitePage,
    SiteSettings,
)
from cms.gallery_defaults import GALLERY_IMAGES
from cms.month_hook_defaults import MONTH_HOOK_DEFAULTS
from cms.salon_defaults import (
    SALON_BODY,
    SALON_BODY_LEGACY,
    SALON_PROFILE_BODY,
    SALON_PROFILE_TITLE,
    SALON_SUBTITLE,
    SALON_TITLE,
    SALON_TITLE_LEGACY,
)
from cms.service_defaults import (
    SERVICE_BODY,
    SERVICE_BODY_LEGACY,
    SERVICE_CTA_PRIMARY,
    SERVICE_SUBTITLE,
    SERVICE_TITLE,
)
from cms.season_tip_defaults import SEASON_TIP_DEFAULTS
from cms.warming_defaults import (
    WARMING_BODY,
    WARMING_BODY_LEGACY,
    WARMING_CTA_PRIMARY,
    WARMING_CTA_SECONDARY,
    WARMING_SUBTITLE,
    WARMING_TITLE,
)

# Adjust: public brand name — seed upgrades legacy "Resurs" once without --force
BRAND_NAME = "EGentid Spa & Service"
BRAND_NAME_LEGACY = "EGentid Spa & Resurs"
CONTACT_EMAIL = "info@egentidspaservice.se"
CONTACT_EMAIL_LEGACY = "info@egentidsparesurs.se"
DEFAULT_META_DESCRIPTION = (
    "Fotvård, spa-pedikyr och värmande manikyr. Boka egentid hos EGentid Spa & Service."
)
DEFAULT_META_DESCRIPTION_LEGACY = (
    "Fotvård, spa-pedikyr och värmande manikyr. Boka egentid hos EGentid Spa & Resurs."
)
TREATMENTS_META_DESCRIPTION = (
    "Fotvård, handvård och massage med priser hos EGentid Spa & Service."
)
TREATMENTS_META_DESCRIPTION_LEGACY = (
    "Fotvård, handvård och massage med priser hos EGentid Spa & Resurs."
)


def _logo_has_white_background(image_field) -> bool:
    """True when corner pixels are still opaque white (legacy square logo export)."""
    if _file_missing(image_field):
        return False
    try:
        from PIL import Image

        img = Image.open(image_field.path).convert("RGBA")
        w, h = img.size
        for x, y in ((0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1)):
            r, g, b, a = img.getpixel((x, y))
            if a > 200 and r > 240 and g > 240 and b > 240:
                return True
    except Exception:
        return False
    return False


def _ensure_webp(image_field):
    """Write a .webp sibling next to a saved ImageField (for <picture> tags)."""
    if not image_field or not image_field.name:
        return
    try:
        path = Path(image_field.path)
    except Exception:
        return
    if not path.exists() or path.suffix.lower() not in {".jpg", ".jpeg", ".png"}:
        return
    webp = path.with_suffix(".webp")
    try:
        from PIL import Image

        img = Image.open(path)
        if path.suffix.lower() == ".png":
            img = img.convert("RGBA")
        else:
            img = img.convert("RGB")
        img.save(webp, "WEBP", quality=80, method=6)
    except Exception:
        pass


def _file_missing(image_field):
    """True if the ImageField has no file on disk."""
    if not image_field or not image_field.name:
        return True
    try:
        return not Path(image_field.path).exists()
    except Exception:
        return True


def _save_image(field, src_path: Path, dest_name: str):
    """Copy a static image onto an ImageField and ensure WebP exists."""
    if not src_path.exists():
        return
    with src_path.open("rb") as fh:
        field.save(dest_name, File(fh), save=True)
    _ensure_webp(field)


class Command(BaseCommand):
    help = (
        "Load starter content. By default preserves existing CMS text "
        "(admin edits). Use --force to reset from defaults."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help=(
                "Overwrite pages, tips, and blocks with seed defaults. "
                "Destroys admin edits — only for intentional reset."
            ),
        )

    def handle(self, *args, **options):
        force = options["force"]
        static_img = Path(__file__).resolve().parents[3] / "static" / "img"
        settings = SiteSettings.load()
        # Rule: never wipe admin SiteSettings text unless --force
        if force:
            settings.site_name = BRAND_NAME
            settings.tagline = "Skönhet & avkoppling – med en värmande touch!"
            settings.email = CONTACT_EMAIL
            settings.phone = ""
            settings.address = "Egen ingång på nedervåningen"
            settings.opening_hours = ""
            settings.footer_text = (
                "En lugn oas för fotvård, handvård och värmande behandlingar."
            )
        else:
            # Fill only blank starter fields (first deploy)
            if not (settings.site_name or "").strip():
                settings.site_name = BRAND_NAME
            if not (settings.tagline or "").strip():
                settings.tagline = "Skönhet & avkoppling – med en värmande touch!"
            if settings.email in ("", CONTACT_EMAIL_LEGACY):
                settings.email = CONTACT_EMAIL
            if not (settings.address or "").strip():
                settings.address = "Egen ingång på nedervåningen"
            if not (settings.footer_text or "").strip():
                settings.footer_text = (
                    "En lugn oas för fotvård, handvård och värmande behandlingar."
                )
        if not force:
            # One-time rename Spa & Resurs → Spa & Service (keeps other admin edits)
            settings_updates = []
            if (settings.site_name or "").strip() == BRAND_NAME_LEGACY:
                settings.site_name = BRAND_NAME
                settings_updates.append("site_name")
            if (
                (settings.default_meta_description or "").strip()
                == DEFAULT_META_DESCRIPTION_LEGACY
            ):
                settings.default_meta_description = DEFAULT_META_DESCRIPTION
                settings_updates.append("default_meta_description")
            if settings_updates:
                settings.save(update_fields=settings_updates)
        logo_src = static_img / "logo.png"
        if not logo_src.exists():
            logo_src = static_img / "logo.jpg"
        # Restore or upgrade logo from static (e.g. after redeploy or brand refresh).
        logo_name = (settings.logo.name or "").lower()
        needs_logo = (
            force
            or _file_missing(settings.logo)
            or logo_name.endswith("logo.jpg")
            or (not force and _logo_has_white_background(settings.logo))
        )
        if logo_src.exists() and needs_logo:
            _save_image(settings.logo, logo_src, logo_src.name)
        settings.save()
        _ensure_webp(settings.logo)

        pages = {
            SitePage.PageKey.HOME: {
                "title": "En stund som bara är din!",
                "subtitle": "Värme • Beröring • Omtanke",
                "body": (
                    "En liten personlig salong i Linköping där du får lämna vardagen en stund "
                    "och bara bli omhändertagen."
                ),
                "hero": "hero-feet.jpg",
            },
            SitePage.PageKey.SALON: {
                "title": SALON_TITLE,
                "subtitle": SALON_SUBTITLE,
                "body": SALON_BODY,
                "hero": "gallery-1.jpg",
            },
            SitePage.PageKey.TREATMENTS: {
                "title": "Behandlingar & priser",
                "subtitle": "En stund av värme, omtanke och välvårdade händer och fötter.",
                "body": (
                    "Hos EGentid får du behandlingar där nagelvård och fotvård kombineras "
                    "med mjukgörande vård, massage och avkoppling."
                ),
                "hero": "hand-massage.jpg",
            },
            SitePage.PageKey.WARMING: {
                "title": WARMING_TITLE,
                "subtitle": WARMING_SUBTITLE,
                "body": WARMING_BODY,
                "cta_primary": WARMING_CTA_PRIMARY,
                "cta_secondary": WARMING_CTA_SECONDARY,
                "hero": "hand-massage.jpg",
            },
            SitePage.PageKey.SEASONS: {
                "title": "Välmående fötter och händer – året runt!",
                "subtitle": "",
                "body": (
                    "Många tror att en spa-pedikyr på våren räcker för sommaren, men fötterna "
                    "och händerna behöver regelbunden omsorg. Kyla, värme och torr luft "
                    "påverkar huden året om, och utan vård kan förhårdnader, sprickor och "
                    "nariga händer uppstå.\n\n"
                    "Genom att unna dig en behandling var 6:e–8:e vecka håller du både fötter "
                    "och händer mjuka och friska – oavsett säsong. Läs vidare för att se "
                    "varför spa-pedikyr och värmande manikyr alltid är en bra idé!"
                ),
                "hero": None,
            },
            SitePage.PageKey.GALLERY: {
                "title": "Galleri",
                "subtitle": "Bilder från salongen och behandlingarna.",
                "body": "",
                "hero": None,
            },
            SitePage.PageKey.BOOKING: {
                "title": "Boka tid",
                "subtitle": "Välj en ledig lucka och fyll i dina uppgifter.",
                "body": "Du får en bekräftelse direkt när bokningen är sparad.",
                "hero": None,
            },
            SitePage.PageKey.CONTACT: {
                "title": "Kontakt",
                "subtitle": "Hör av dig – jag svarar så snart jag kan.",
                "body": (
                    "Har du frågor om behandlingar, öppettider eller hur jag kan hjälpa dig "
                    "som resurs? Skicka ett meddelande via formuläret."
                ),
                "hero": None,
            },
            SitePage.PageKey.SERVICE: {
                "title": SERVICE_TITLE,
                "subtitle": SERVICE_SUBTITLE,
                "body": SERVICE_BODY,
                "cta_primary": SERVICE_CTA_PRIMARY,
                "hero": None,
            },
        }

        for key, data in pages.items():
            page_defaults = {
                "title": data["title"],
                "subtitle": data["subtitle"],
                "body": data["body"],
                "is_published": True,
            }
            if data.get("cta_primary") is not None:
                page_defaults["cta_primary"] = data["cta_primary"]
            if data.get("cta_secondary") is not None:
                page_defaults["cta_secondary"] = data["cta_secondary"]
            page, created = SitePage.objects.get_or_create(
                key=key,
                defaults=page_defaults,
            )
            if force and not created:
                page.title = data["title"]
                page.subtitle = data["subtitle"]
                page.body = data["body"]
                page.is_published = True
                if "cta_primary" in data:
                    page.cta_primary = data["cta_primary"]
                if "cta_secondary" in data:
                    page.cta_secondary = data["cta_secondary"]
                page.save()
            elif (
                key == SitePage.PageKey.WARMING
                and not force
                and (page.body or "").strip() == WARMING_BODY_LEGACY.strip()
            ):
                # One-time upgrade from the old short warming copy
                page.title = WARMING_TITLE
                page.subtitle = WARMING_SUBTITLE
                page.body = WARMING_BODY
                page.cta_primary = WARMING_CTA_PRIMARY
                page.cta_secondary = WARMING_CTA_SECONDARY
                page.save(
                    update_fields=[
                        "title",
                        "subtitle",
                        "body",
                        "cta_primary",
                        "cta_secondary",
                    ]
                )
            elif (
                key == SitePage.PageKey.WARMING
                and not force
                and not (page.cta_primary or "").strip()
                and not (page.cta_secondary or "").strip()
            ):
                # Fill empty CTA labels once without overwriting admin edits
                page.cta_primary = WARMING_CTA_PRIMARY
                page.cta_secondary = WARMING_CTA_SECONDARY
                page.save(update_fields=["cta_primary", "cta_secondary"])
            elif (
                key == SitePage.PageKey.SALON
                and not force
                and (
                    (page.title or "").strip() == SALON_TITLE_LEGACY.strip()
                    or (page.body or "").strip() == SALON_BODY_LEGACY.strip()
                )
            ):
                # One-time upgrade from the old Om copy
                page.title = SALON_TITLE
                page.subtitle = SALON_SUBTITLE
                page.body = SALON_BODY
                page.save(update_fields=["title", "subtitle", "body"])
            elif (
                key == SitePage.PageKey.SALON
                and not force
                and not (page.body or "").strip()
            ):
                # Restore body after retired presentation layout (empty page body)
                page.body = SALON_BODY
                page.save(update_fields=["body"])
            elif (
                key == SitePage.PageKey.SERVICE
                and not force
                and (page.body or "").strip() == SERVICE_BODY_LEGACY.strip()
            ):
                page.title = SERVICE_TITLE
                page.subtitle = SERVICE_SUBTITLE
                page.body = SERVICE_BODY
                page.cta_primary = SERVICE_CTA_PRIMARY
                page.save(
                    update_fields=["title", "subtitle", "body", "cta_primary"]
                )
            elif (
                key == SitePage.PageKey.SERVICE
                and not force
                and not (page.cta_primary or "").strip()
            ):
                page.cta_primary = SERVICE_CTA_PRIMARY
                page.save(update_fields=["cta_primary"])
            if created or force:
                if key == SitePage.PageKey.TREATMENTS:
                    page.meta_title = ""
                    page.meta_description = TREATMENTS_META_DESCRIPTION
                    page.save(update_fields=["meta_title", "meta_description"])
            if data["hero"]:
                src = static_img / data["hero"]
                if src.exists() and _file_missing(page.hero_image):
                    _save_image(page.hero_image, src, data["hero"])
                elif page.hero_image:
                    _ensure_webp(page.hero_image)

        # Prislista removed from the public site — hide any leftover CMS page
        SitePage.objects.filter(key=SitePage.PageKey.PRICES).update(is_published=False)

        # Retired home feature blocks — remove if still in DB (local or after deploy)
        ContentBlock.objects.filter(
            page__key=SitePage.PageKey.HOME,
            title__in=("Händer får massage", "Mer än bara behandling"),
        ).delete()

        # Emma profile under Boka on Om — Admin → Sidor → Om → Innehållsblock
        salon_page = SitePage.objects.get(key=SitePage.PageKey.SALON)
        if force:
            ContentBlock.objects.filter(page=salon_page).delete()
        profile = ContentBlock.objects.filter(page=salon_page).first()
        if force or not profile:
            ContentBlock.objects.create(
                page=salon_page,
                title=SALON_PROFILE_TITLE,
                body=SALON_PROFILE_BODY,
                sort_order=0,
                is_visible=True,
            )
        elif not (profile.body or "").strip():
            profile.title = SALON_PROFILE_TITLE
            profile.body = SALON_PROFILE_BODY
            profile.is_visible = True
            profile.save(update_fields=["title", "body", "is_visible"])
        elif not force and BRAND_NAME_LEGACY in (profile.body or ""):
            profile.body = profile.body.replace(BRAND_NAME_LEGACY, BRAND_NAME)
            profile.save(update_fields=["body"])

        treatments = SitePage.objects.get(key=SitePage.PageKey.TREATMENTS)
        if (
            not force
            and (treatments.meta_description or "").strip()
            == TREATMENTS_META_DESCRIPTION_LEGACY
        ):
            treatments.meta_description = TREATMENTS_META_DESCRIPTION
            treatments.save(update_fields=["meta_description"])
        # Adjust: Behandlingar & priser copy — Admin → Sidor → Behandlingar & priser
        treatment_blocks = [
            ("Fötter", 1, "", ""),
            (
                "Evig Lycka – Spa-pedikyr",
                2,
                (
                    "425 kr · ca 60 min\n\n"
                    "En klassisk spa-pedikyr för dig som vill få välvårdade naglar och mjukare fötter.\n\n"
                    "## Det här ingår:\n"
                    "• Naglarna klipps och filas\n"
                    "• Nagelbanden vårdas\n"
                    "• Fötterna mjukas upp\n"
                    "• Fotvård med skrubb\n"
                    "• Vårdande kräm\n"
                    "• Avslutande fotmassage\n\n"
                    "## Passar dig som vill:\n"
                    "få ordning på naglarna, mjuka upp torra fötter och samtidigt njuta av en lugn stund."
                ),
                "hero-feet.jpg",
            ),
            (
                "Gyllene Beröring – Värmande paraffinpedikyr",
                3,
                (
                    "499 kr · ca 75 min\n\n"
                    "Spa-pedikyr + värmande paraffin för dig som vill ge fötterna lite extra omsorg.\n\n"
                    "## Det här ingår:\n"
                    "• Allt som ingår i Spa-pedikyr\n"
                    "• Vårdande skrubb\n"
                    "• Fotmassage\n"
                    "• Värmande paraffinbehandling\n\n"
                    "## Passar dig som:\n"
                    "är torr om fötterna, ofta fryser om fötterna eller bara älskar känslan av värme och mjukhet."
                ),
                "hero-feet.jpg",
            ),
            ("Händer", 4, "", ""),
            (
                "Lugnande Händer – Manikyr med lack",
                5,
                (
                    "400 kr · ca 45 min\n\n"
                    "Välvårdade naglar och händer med en stunds avkoppling.\n\n"
                    "## Det här ingår:\n"
                    "• Naglarna klipps/filas och formas\n"
                    "• Nagelbandsvård\n"
                    "• Handmassage\n"
                    "• Lack om du önskar"
                ),
                "hand-massage.jpg",
            ),
            (
                "Ren Omsorg – Värmande paraffinmanikyr",
                6,
                (
                    "499 kr · ca 60 min\n\n"
                    "Manikyr + värmande paraffin för torra och trötta händer.\n\n"
                    "## Det här ingår:\n"
                    "• Nagelvård och formning\n"
                    "• Nagelbandsvård\n"
                    "• Handmassage\n"
                    "• Värmande paraffinbehandling\n"
                    "• Vårdande avslut"
                ),
                "hand-massage.jpg",
            ),
            (
                "Kunglig Avkoppling – Händer & fötter",
                7,
                (
                    "699 kr · ca 105–120 min\n\n"
                    "En längre stund för dig som vill ge både händer och fötter lite extra omsorg.\n\n"
                    "## Det här ingår:\n"
                    "• Spa-pedikyr\n"
                    "• Manikyr & nagelvård\n"
                    "• Handmassage\n"
                    "• Fot- och vadmassage\n"
                    "• Vårdande produkter\n\n"
                    "## Vill du ha extra värme?\n"
                    "Lägg till värmande paraffin för händer eller fötter: +75 kr\n"
                    "Både händer och fötter: +125 kr"
                ),
                "hand-massage.jpg",
            ),
            ("Massage", 8, "", ""),
            (
                "Lugnande Stund – Hand- eller fotmassage",
                9,
                (
                    "250 kr · ca 30 min\n\n"
                    "En enkel och skön behandling när du framför allt vill ha massage och avkoppling."
                ),
                "hand-massage.jpg",
            ),
        ]
        if force or not treatments.blocks.exists():
            if force:
                ContentBlock.objects.filter(page=treatments).delete()
            if not treatments.blocks.exists():
                for title, order, body, image_name in treatment_blocks:
                    block = ContentBlock.objects.create(
                        page=treatments,
                        title=title,
                        body=body,
                        sort_order=order,
                    )
                    if image_name:
                        src = static_img / image_name
                        if src.exists():
                            _save_image(block.image, src, image_name)

        # Gallery — static/img/gallery/ + Admin → Galleribilder
        gallery_dir = static_img / "gallery"
        legacy_gallery_names = {"gallery-1.jpg", "hand-massage.jpg", "hero-feet.jpg"}
        existing_gallery_names = {
            Path(gi.image.name).name
            for gi in GalleryImage.objects.all()
            if gi.image and gi.image.name
        }
        if force or (
            GalleryImage.objects.exists()
            and existing_gallery_names
            and existing_gallery_names.issubset(legacy_gallery_names)
            and gallery_dir.is_dir()
        ):
            GalleryImage.objects.all().delete()
        for sort_order, (filename, title, caption) in enumerate(GALLERY_IMAGES):
            src = gallery_dir / filename
            if not src.exists():
                continue
            gi = GalleryImage.objects.filter(image__endswith=f"/{filename}").first()
            if not gi:
                gi = GalleryImage(
                    title=title,
                    caption=caption,
                    sort_order=sort_order,
                    is_visible=True,
                )
                _save_image(gi.image, src, filename)
            else:
                updates = []
                if force or gi.title != title:
                    gi.title = title
                    updates.append("title")
                if force or gi.caption != caption:
                    gi.caption = caption
                    updates.append("caption")
                if gi.sort_order != sort_order:
                    gi.sort_order = sort_order
                    updates.append("sort_order")
                if updates:
                    gi.save(update_fields=updates)
                if force or _file_missing(gi.image):
                    _save_image(gi.image, src, filename)
                else:
                    _ensure_webp(gi.image)

        # Året runt: long month copy in CMS → Säsongstips. Page shows current month.
        for month, data in SEASON_TIP_DEFAULTS.items():
            tip, created = SeasonTip.objects.get_or_create(
                month=month,
                defaults={
                    "title": data["title"],
                    "icon": data["icon"],
                    "body": data["body"],
                    "is_featured": False,
                    "is_visible": True,
                    "closing_icon": "",
                    "closing_label": "",
                    "closing_body": "",
                    "closing_cta": "",
                },
            )
            if force and not created:
                tip.title = data["title"]
                tip.icon = data["icon"]
                tip.body = data["body"]
                tip.is_featured = False
                tip.is_visible = True
                tip.closing_icon = ""
                tip.closing_label = ""
                tip.closing_body = ""
                tip.closing_cta = ""
                tip.save()
                tip.items.all().delete()

        # Retired Året runt closing block — remove if still in DB
        ContentBlock.objects.filter(
            page__key=SitePage.PageKey.SEASONS,
            title="🌿 Dina händer och fötter följer dig hela året",
        ).delete()

        # Home “Känner du igen” — Admin → CMS → Känner du igen
        for month, data in MONTH_HOOK_DEFAULTS.items():
            hook, created = MonthHook.objects.get_or_create(
                month=month,
                defaults={
                    "icon": data["icon"],
                    "quote": data["quote"],
                    "body": data["body"],
                    "cta": data["cta"],
                    "is_visible": True,
                },
            )
            if force and not created:
                hook.icon = data["icon"]
                hook.quote = data["quote"]
                hook.body = data["body"]
                hook.cta = data["cta"]
                hook.is_visible = True
                hook.save()

        services = [
            (
                "Evig Lycka – Spa-pedikyr",
                60,
                425,
                "Naglar klipps och filas, fötterna mjukas upp, avslutas med vårdande kräm.",
            ),
            (
                "Gyllene Beröring – Värmande paraffinpedikyr",
                75,
                499,
                "Spa-pedikyr med nagelvård och fotfilning, följt av värmande paraffin.",
            ),
            (
                "Lugnande Händer – Manikyr med lack",
                45,
                400,
                "Nagelband, handmassage och formning. Lack om så önskas.",
            ),
            (
                "Ren Omsorg – Värmande paraffinmanikyr",
                60,
                499,
                "Nagelbandsvård, handmassage och värmande paraffin.",
            ),
            (
                "Kunglig Avkoppling – Händer & fötter",
                120,
                699,
                "Spa-pedikyr och manikyr med massage för händer och fötter.",
            ),
            (
                "Lugnande Stund – Hand- eller fotmassage",
                30,
                250,
                "Massage med fokus på avkoppling och välbefinnande.",
            ),
        ]
        # Deactivate old seed services that no longer match Behandlingar & priser.
        Service.objects.filter(
            slug__in=[
                "spa-pedikyr",
                "varmande-manikyr",
                "paraffinbehandling",
                "kunglig-avkoppling-kombo-behandling",
            ]
        ).update(is_active=False)
        for order, (name, mins, price, desc) in enumerate(services):
            service, created = Service.objects.get_or_create(
                slug=slugify(name),
                defaults={
                    "name": name,
                    "duration_minutes": mins,
                    "price_sek": price,
                    "description": desc,
                    "is_active": True,
                    "sort_order": order,
                },
            )
            if force and not created:
                service.name = name
                service.duration_minutes = mins
                service.price_sek = price
                service.description = desc
                service.is_active = True
                service.sort_order = order
                service.save()

        if not WeeklyAvailability.objects.exists():
            for weekday in range(0, 5):  # Mon–Fri
                WeeklyAvailability.objects.create(
                    weekday=weekday,
                    start_time=time(9, 0),
                    end_time=time(16, 0),
                    slot_minutes=60,
                    is_active=True,
                )

        today = date.today()
        created = generate_slots_for_range(today, today + timedelta(days=28))
        mode = "force overwrite" if force else "preserve existing CMS text"
        self.stdout.write(self.style.SUCCESS(f"Seed klar ({mode}). Nya luckor: {created}"))
