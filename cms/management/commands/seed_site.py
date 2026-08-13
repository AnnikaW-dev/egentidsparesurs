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
    SeasonTip,
    SeasonTipItem,
    SitePage,
    SiteSettings,
)


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
    help = "Load starter content matching egentidsparesurs.wordpress.com"

    def handle(self, *args, **options):
        static_img = Path(__file__).resolve().parents[3] / "static" / "img"
        settings = SiteSettings.load()
        settings.site_name = "EGentid Spa & Resurs"
        settings.tagline = "Skönhet & avkoppling – med en värmande touch!"
        settings.email = "info@egentidsparesurs.se"
        settings.phone = ""
        settings.address = "Egen ingång på nedervåningen"
        settings.opening_hours = "Bokning krävs – se lediga tider under Boka."
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
                "title": "Skönhet & avkoppling med en värmande touch!",
                "subtitle": "",
                "body": (
                    "Ge dina fötter den omsorg de förtjänar! Unna dig en avkopplande "
                    "spa-pedikyr som återfuktar, mjukar upp och ger ny energi till trötta fötter. "
                    "Perfekt för alla årstider!"
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
                "title": "Behandlingar",
                "subtitle": "Unna dig en stund av värme, lugn och omtanke.",
                "body": (
                    "Här hittar du behandlingar för händer och fötter med fokus på avkoppling, "
                    "mjukgörande vård och välmående."
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
            SitePage.PageKey.PRICES: {
                "title": "Prislista",
                "subtitle": "Unna dig en stund av värme, lugn och omtanke.",
                "body": (
                    "Här hittar du behandlingar för händer och fötter med fokus på avkoppling, "
                    "mjukgörande vård och välmående."
                ),
                "hero": None,
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
            page, _ = SitePage.objects.update_or_create(
                key=key,
                defaults={
                    "title": data["title"],
                    "subtitle": data["subtitle"],
                    "body": data["body"],
                    "is_published": True,
                },
            )
            if data["hero"]:
                src = static_img / data["hero"]
                if src.exists() and _file_missing(page.hero_image):
                    _save_image(page.hero_image, src, data["hero"])
                elif page.hero_image:
                    _ensure_webp(page.hero_image)

        home = SitePage.objects.get(key=SitePage.PageKey.HOME)
        ContentBlock.objects.filter(page=home).delete()
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
        ContentBlock.objects.filter(page=treatments).delete()
        treatment_blocks = [
            (
                "Evig Lycka – Spa-pedikyr",
                1,
                (
                    "425 kr | ca 60 min\n\n"
                    "Ge dina fötter en välförtjänt paus.\n"
                    "En avkopplande spa-pedikyr där naglar klipps och filas, fötterna mjukas upp "
                    "och behandlingen avslutas med vårdande kräm.\n\n"
                    "## Passar dig som:\n"
                    "✔ få mjukare fötter\n"
                    "✔ vårda torra fötter\n"
                    "✔ njuta av en lugn stund för dig själv"
                ),
                "hero-feet.jpg",
            ),
            (
                "Gyllene Beröring – Värmande paraffinpedikyr",
                2,
                (
                    "499 kr | ca 75 min\n\n"
                    "En extra varm och vårdande behandling där spa-pedikyr kombineras med värmande paraffin.\n"
                    "Fötterna får först omsorg med nagelvård och uppmjukning, därefter får de njuta av "
                    "den behagliga värmen från paraffin.\n\n"
                    "## Passar dig som:\n"
                    "✔ har torra fötter och vill ge huden extra fukt\n"
                    "✔ ofta fryser om fötterna\n"
                    "✔ känner dig stel och uppskattar värmande behandlingar\n"
                    "✔ vill unna dig en lugn stund med fokus på välmående"
                ),
                "hero-feet.jpg",
            ),
            (
                "Lugnande Händer – Manikyr med lack",
                3,
                (
                    "350–400 kr | ca 45 min\n\n"
                    "Välvårdade händer med en stund av avkoppling.\n"
                    "Behandlingen innehåller nagelbandsvård, formning av naglar, handmassage och lack om du önskar."
                ),
                "hand-massage.jpg",
            ),
            (
                "Ren Omsorg – Värmande paraffinmanikyr",
                4,
                (
                    "499 kr | ca 60 min\n\n"
                    "En mjuk och värmande behandling för torra och trötta händer.\n"
                    "Med handmassage och paraffin får händerna:\n"
                    "✔ extra fukt\n"
                    "✔ mjukare hud\n"
                    "✔ en avslappnande stund"
                ),
                "hand-massage.jpg",
            ),
            (
                "Kunglig Avkoppling – Kombo behandling",
                5,
                (
                    "800 kr | ca 120 min\n\n"
                    "En komplett stund för dig som vill njuta lite extra.\n"
                    "Spa-pedikyr och manikyr kombineras med värmande paraffin och massage för både händer och fötter."
                ),
                "hand-massage.jpg",
            ),
            (
                "Lugnande Stund – Hand- eller fotmassage",
                6,
                (
                    "250 kr | ca 30 min\n\n"
                    "En enkel behandling med fokus på avkoppling och välbefinnande."
                ),
                "hand-massage.jpg",
            ),
            (
                "Varför värmande behandlingar?",
                7,
                (
                    "Värme är inte bara skönt – det ger en härlig känsla av avslappning.\n"
                    "Paraffinbehandling används ofta för att:\n"
                    "✔ mjuka upp torr hud\n"
                    "✔ ge händer och fötter extra fukt\n"
                    "✔ skapa en behaglig värme\n"
                    "✔ hjälpa kroppen att slappna av"
                ),
                "",
            ),
        ]
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

        prices_page = SitePage.objects.get(key=SitePage.PageKey.PRICES)
        ContentBlock.objects.filter(page=prices_page).delete()
        for title, order, body, _image in treatment_blocks:
            ContentBlock.objects.create(
                page=prices_page,
                title=title,
                body=body,
                sort_order=order,
            )

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

        # Året runt: full month copy editable in admin; featured = April by default.
        SeasonTip.objects.update(is_featured=False)
        season_defaults = [
            (
                4,
                "April – Vår på riktigt",
                "🌸",
                True,
                [
                    (
                        "Dags att ta fram sandalerna!",
                        "Ge fötterna en fräsch start",
                    ),
                    (
                        "Mildare luft = Fortfarande torr hud",
                        "Huden vänjer sig långsamt vid förändringar",
                    ),
                    (
                        "Boost för huden",
                        "Värmebehandlingar ger ökad cirkulation och mjukar upp huden",
                    ),
                ],
                {
                    "closing_icon": "💡",
                    "closing_label": "Kort sagt:",
                    "closing_body": "Ge din hud och dina fötter en nystart efter vintern –",
                    "closing_cta": "boka din behandling nu!",
                },
            ),
            (
                3,
                "Mars – Vårens första månad",
                "🌱",
                False,
                [
                    (
                        "Dags att vakna upp huden",
                        "Efter en lång vinter behöver huden näring och fukt",
                    ),
                    (
                        "Förbered fötterna för öppna skor",
                        "Bort med torr hud och ge naglarna vårkänsla",
                    ),
                    (
                        "Vårtrötthet?",
                        "En avslappnande behandling ger ny energi",
                    ),
                ],
                {
                    "closing_icon": "💡",
                    "closing_label": "Kort sagt:",
                    "closing_body": "Ge händer och fötter en vårstart –",
                    "closing_cta": "boka din behandling nu!",
                },
            ),
            (1, "Januari – Nytt år, mjuka fötter", "❄️", False, [], {}),
            (2, "Februari – Vintervård", "❄️", False, [], {}),
            (5, "Maj – Förbered dig för sommaren!", "☀️", False, [], {}),
            (6, "Juni – Sommarfötter", "☀️", False, [], {}),
            (7, "Juli – Sol och bad", "☀️", False, [], {}),
            (8, "Augusti – Sensommar", "🍂", False, [], {}),
            (9, "September – Hösten börjar", "🍂", False, [], {}),
            (10, "Oktober – Värmande omsorg", "🍂", False, [], {}),
            (11, "November – Mot kylan", "❄️", False, [], {}),
            (12, "December – Egentid i julruschen", "❄️", False, [], {}),
        ]
        for month, title, icon, featured, items, closing in season_defaults:
            tip, _ = SeasonTip.objects.update_or_create(
                month=month,
                defaults={
                    "title": title,
                    "icon": icon,
                    "body": "",
                    "is_featured": featured,
                    "is_visible": True,
                    "closing_icon": closing.get("closing_icon", "💡"),
                    "closing_label": closing.get("closing_label", "Kort sagt:"),
                    "closing_body": closing.get("closing_body", ""),
                    "closing_cta": closing.get(
                        "closing_cta", "boka din behandling nu!"
                    ),
                },
            )
            if items:
                tip.items.all().delete()
                for order, (headline, description) in enumerate(items):
                    SeasonTipItem.objects.create(
                        tip=tip,
                        headline=headline,
                        description=description,
                        sort_order=order,
                    )

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
                375,
                "Nagelband, handmassage och formning. Lack om så önskas (350–400 kr).",
            ),
            (
                "Ren Omsorg – Värmande paraffinmanikyr",
                60,
                499,
                "Nagelbandsvård, handmassage och värmande paraffin.",
            ),
            (
                "Kunglig Avkoppling – Kombo behandling",
                120,
                800,
                "Pedikyr och manikyr med paraffin och massage för händer och fötter.",
            ),
            (
                "Lugnande Stund – Hand- eller fotmassage",
                30,
                250,
                "Massage med fokus på avkoppling och välbefinnande.",
            ),
        ]
        # Deactivate old seed services that no longer match the prislista.
        Service.objects.filter(
            slug__in=[
                "spa-pedikyr",
                "varmande-manikyr",
                "paraffinbehandling",
            ]
        ).update(is_active=False)
        for order, (name, mins, price, desc) in enumerate(services):
            Service.objects.update_or_create(
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
        self.stdout.write(self.style.SUCCESS(f"Seed klar. Nya luckor: {created}"))
