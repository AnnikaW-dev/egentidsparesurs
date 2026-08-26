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
from cms.month_hook_defaults import MONTH_HOOK_DEFAULTS
from cms.season_tip_defaults import SEASON_TIP_DEFAULTS, SEASONS_CLOSING


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
    if webp.exists():
        return
    try:
        from PIL import Image

        Image.open(path).convert("RGB").save(webp, "WEBP", quality=80, method=6)
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
            settings.site_name = "EGentid Spa & Resurs"
            settings.tagline = "Skönhet & avkoppling – med en värmande touch!"
            settings.email = "info@egentidsparesurs.se"
            settings.phone = ""
            settings.address = "Egen ingång på nedervåningen"
            settings.opening_hours = ""
            settings.footer_text = (
                "En lugn oas för fotvård, handvård och värmande behandlingar."
            )
        else:
            # Fill only blank starter fields (first deploy)
            if not (settings.site_name or "").strip():
                settings.site_name = "EGentid Spa & Resurs"
            if not (settings.tagline or "").strip():
                settings.tagline = "Skönhet & avkoppling – med en värmande touch!"
            if not (settings.email or "").strip():
                settings.email = "info@egentidsparesurs.se"
            if not (settings.address or "").strip():
                settings.address = "Egen ingång på nedervåningen"
            if not (settings.footer_text or "").strip():
                settings.footer_text = (
                    "En lugn oas för fotvård, handvård och värmande behandlingar."
                )
        logo_src = static_img / "logo.jpg"
        # Always restore logo when missing on disk (common after Render redeploy without disk).
        if logo_src.exists() and _file_missing(settings.logo):
            _save_image(settings.logo, logo_src, "logo.jpg")
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
                "title": "Min salong – En plats för avkoppling och fokus",
                "subtitle": "",
                "body": (
                    "Välkommen till min salong, en lugn oas inredd i beige, brunt och naturliga "
                    "färger för att skapa en varm och avslappnad atmosfär. Här vill jag att du "
                    "ska känna dig trygg, omhändertagen och kunna släppa stressen.\n\n"
                    "När du kommer hit för en behandling får du njuta av en rogivande miljö där "
                    "fokus ligger helt på dig och ditt välmående.\n\n"
                    "Om du istället vill diskutera hur jag kan hjälpa dig som resurs, kan vi slå "
                    "oss ner i min sköna soffa och prata i lugn och ro. Här ska du kunna koppla "
                    "bort allt annat och fokusera på hur vi tillsammans kan skapa mer egentid "
                    "och lätthet i vardagen.\n\n"
                    "Min salong ligger på nedervåningen i mitt hem med en egen ingång, vilket "
                    "gör det enkelt och avskilt för dig som kund.\n\n"
                    "Välkommen att boka en stund för dig själv!"
                ),
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
                "title": "Värmande behandlingar",
                "subtitle": "Värme är inte bara skönt – det är också läkande och avslappnande!",
                "body": (
                    "Ökar blodcirkulationen.\n\n"
                    "Mjukar upp stela och ömma leder.\n\n"
                    "Lindrar torr hud och sprickor.\n\n"
                    "Perfekt vid reumatism, artrit och ledvärk."
                ),
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
                "title": "Service",
                "subtitle": "Mer än behandling – hjälp som sparar din tid och energi.",
                "body": (
                    "Behöver du avlastning med administrativa uppgifter eller en lugn stund "
                    "för att prata igenom vad som tar tid och kraft i vardagen?\n\n"
                    "Här kan du släppa stressen och låta mig ta hand om det som ger dig mer "
                    "egentid. Hör av dig via kontaktformuläret så hittar vi en lösning "
                    "tillsammans."
                ),
                "hero": None,
            },
        }

        for key, data in pages.items():
            page, created = SitePage.objects.get_or_create(
                key=key,
                defaults={
                    "title": data["title"],
                    "subtitle": data["subtitle"],
                    "body": data["body"],
                    "is_published": True,
                },
            )
            if force and not created:
                page.title = data["title"]
                page.subtitle = data["subtitle"]
                page.body = data["body"]
                page.is_published = True
                page.save()
            if created or force:
                if key == SitePage.PageKey.TREATMENTS:
                    page.meta_title = ""
                    page.meta_description = (
                        "Fotvård, handvård och massage med priser hos EGentid Spa & Resurs."
                    )
                    page.save(update_fields=["meta_title", "meta_description"])
            if data["hero"]:
                src = static_img / data["hero"]
                if src.exists() and _file_missing(page.hero_image):
                    _save_image(page.hero_image, src, data["hero"])
                elif page.hero_image:
                    _ensure_webp(page.hero_image)

        # Prislista removed from the public site — hide any leftover CMS page
        SitePage.objects.filter(key=SitePage.PageKey.PRICES).update(is_published=False)

        home = SitePage.objects.get(key=SitePage.PageKey.HOME)
        if force or not home.blocks.exists():
            if force:
                ContentBlock.objects.filter(page=home).delete()
            if not home.blocks.exists():
                hand = ContentBlock.objects.create(
                    page=home,
                    title="Händer får massage",
                    body=(
                        "Låt stressen rinna av med en lyxig handbehandling! Värmande massage och "
                        "näringsrik vård ger mjuka, återfuktade händer och starka naglar. En stund "
                        "av välbehövlig avkoppling bara för dig."
                    ),
                    sort_order=1,
                )
                hand_src = static_img / "hand-massage.jpg"
                if hand_src.exists() and _file_missing(hand.image):
                    _save_image(hand.image, hand_src, "hand-massage.jpg")
                elif hand.image:
                    _ensure_webp(hand.image)

                ContentBlock.objects.create(
                    page=home,
                    title="Mer än bara behandling",
                    body=(
                        "Oavsett om du vill ha en skön behandling eller hjälp med administrativa "
                        "uppgifter, så är detta en plats där du kan släppa stressen och låta mig ta "
                        "hand om det som sparar din tid och energi. Vad behöver du hjälp med idag?"
                    ),
                    sort_order=2,
                )

        treatments = SitePage.objects.get(key=SitePage.PageKey.TREATMENTS)
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

        # Gallery: create rows if empty, otherwise restore missing files.
        gallery_specs = [
            ("gallery-1.jpg", "Salongen"),
            ("hand-massage.jpg", "Handmassage"),
            ("hero-feet.jpg", "Fotvård"),
        ]
        if not GalleryImage.objects.exists():
            for name, title in gallery_specs:
                src = static_img / name
                if src.exists():
                    gi = GalleryImage(title=title, caption=title, sort_order=0)
                    _save_image(gi.image, src, name)
        else:
            for gi in GalleryImage.objects.all():
                if _file_missing(gi.image):
                    # Best-effort restore from static by filename.
                    name = Path(gi.image.name).name if gi.image.name else ""
                    src = static_img / name
                    if src.exists():
                        _save_image(gi.image, src, name)
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

        # Closing under month tip — Admin → Sidor → Året runt → Innehållsblock
        seasons_page = SitePage.objects.get(key=SitePage.PageKey.SEASONS)
        if force or not seasons_page.blocks.exists():
            if force:
                ContentBlock.objects.filter(page=seasons_page).delete()
            if not seasons_page.blocks.exists():
                ContentBlock.objects.create(
                    page=seasons_page,
                    title=SEASONS_CLOSING["title"],
                    body=SEASONS_CLOSING["body"],
                    sort_order=0,
                    is_visible=True,
                )

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
