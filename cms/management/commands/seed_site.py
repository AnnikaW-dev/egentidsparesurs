"""Seed default pages, services, schedule, and copy from the WordPress site."""

from datetime import date, time, timedelta
from pathlib import Path

from django.core.files import File
from django.core.management.base import BaseCommand
from django.utils.text import slugify

from booking.models import Service, WeeklyAvailability, generate_slots_for_range
from cms.models import ContentBlock, GalleryImage, SeasonTip, SitePage, SiteSettings

# Default treatment copy — used on Behandlingar (and mirrored on Prislista).
TREATMENT_BLOCKS = [
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
            "den behagliga värmen från paraffin som omsluter huden och ger en härlig känsla av "
            "mjukhet och avslappning.\n\n"
            "## Passar dig som:\n"
            "✔ har torra fötter och vill ge huden extra fukt\n"
            "✔ ofta fryser om fötterna\n"
            "✔ känner dig stel och uppskattar värmande behandlingar\n"
            "✔ vill unna dig en lugn stund med fokus på välmående\n\n"
            "Paraffin kan hjälpa huden att kännas mjukare och smidigare, samtidigt som värmen "
            "ger en skön och avslappnande upplevelse."
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


def attach_block_image(block, static_img: Path, filename: str) -> None:
    """Save a static seed image on a ContentBlock and copy its WebP companion."""
    if not filename:
        return
    src = static_img / filename
    if not src.exists():
        return
    with src.open("rb") as fh:
        block.image.save(filename, File(fh), save=True)
    webp_src = src.with_suffix(".webp")
    if webp_src.exists() and block.image:
        Path(block.image.path).with_suffix(".webp").write_bytes(webp_src.read_bytes())


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
        settings.opening_hours = "Enligt bokning\nVardagar efter överenskommelse"
        settings.footer_text = (
            "En lugn oas för fotvård, handvård och värmande behandlingar."
        )
        logo_src = static_img / "logo.jpg"
        if logo_src.exists() and not settings.logo:
            with logo_src.open("rb") as fh:
                settings.logo.save("logo.jpg", File(fh), save=False)
        settings.save()

        pages = {
            SitePage.PageKey.HOME: {
                "title": "Skönhet & avkoppling med en värmande touch!",
                "subtitle": "Unna dig en stund av värme, lugn och omtanke.",
                "body": (
                    "Välkommen till en stund där du får släppa vardagens stress och bara njuta. "
                    "Mina behandlingar återfuktar huden, värmer stela leder och ger både kropp och själ ny energi.\n\n"
                    "Mjuka händer. Lätta fötter. Ett lugnare sinne.\n\n"
                    "Låt mig ta hand om dina händer och fötter med avkopplande behandlingar som mjukar upp huden, "
                    "ökar välmåendet och ger ny energi. Här får du en paus från vardagen – bara för dig."
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
                "title": "Året runt",
                "subtitle": "Tips för händer och fötter genom årstiderna.",
                "body": "Varje månad har sina behov – här är inspiration för din egentid.",
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
            # Only attach hero once — re-saving creates Django name suffixes and breaks WebP pairs.
            if data["hero"] and not page.hero_image:
                src = static_img / data["hero"]
                if src.exists():
                    with src.open("rb") as fh:
                        page.hero_image.save(data["hero"], File(fh), save=True)
                    webp_src = src.with_suffix(".webp")
                    if webp_src.exists() and page.hero_image:
                        Path(page.hero_image.path).with_suffix(".webp").write_bytes(
                            webp_src.read_bytes()
                        )

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
        if hand_src.exists():
            with hand_src.open("rb") as fh:
                hand.image.save("hand-massage.jpg", File(fh), save=True)
            # Keep WebP companion next to the saved upload name.
            webp_src = hand_src.with_suffix(".webp")
            if webp_src.exists() and hand.image:
                dest_webp = Path(hand.image.path).with_suffix(".webp")
                dest_webp.write_bytes(webp_src.read_bytes())

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
        for title, order, body, image_name in TREATMENT_BLOCKS:
            block = ContentBlock.objects.create(
                page=treatments,
                title=title,
                body=body,
                sort_order=order,
            )
            attach_block_image(block, static_img, image_name)

        prices_page = SitePage.objects.get(key=SitePage.PageKey.PRICES)
        ContentBlock.objects.filter(page=prices_page).delete()
        price_blocks = [
            *[(title, order, body) for title, order, body, _image in TREATMENT_BLOCKS],
            (
                "Olja nr 1 – För känslig och mycket torr hud (från 5 år)",
                8,
                (
                    "Återfuktar på djupet och stärker hudens skyddsbarriär. Lugnar eksem och irriterad hud. "
                    "Perfekt för känslig hud och extra torr hud. Passar både barn och vuxna."
                ),
            ),
            (
                "Olja nr 2 – Lyxig & rogivande för normal hud",
                9,
                (
                    "Näringsboost för huden med extra lyster. Stärker elasticitet och stimulerar cellförnyelse. "
                    "Lyxig och rogivande behandling med härliga dofter.\n\n"
                    "Innehåll: Vitamin E, Vitamin A, Omega-9, Omega-6 och Zink."
                ),
            ),
        ]
        for title, order, body in price_blocks:
            ContentBlock.objects.create(
                page=prices_page,
                title=title,
                body=body,
                sort_order=order,
            )

        if not GalleryImage.objects.exists():
            for name, title in [
                ("gallery-1.jpg", "Salongen"),
                ("hand-massage.jpg", "Handmassage"),
                ("hero-feet.jpg", "Fotvård"),
            ]:
                src = static_img / name
                if src.exists():
                    gi = GalleryImage(title=title, caption=title, sort_order=0)
                    with src.open("rb") as fh:
                        gi.image.save(name, File(fh), save=True)

        # Rich monthly tips — home shows the tip for the current calendar month.
        # Adjust: edit Admin → Säsongstips; use ## for headings and ✔ for checklist lines.
        july_body = (
            "Sommaren är en perfekt tid att ge händer och fötter lite extra uppmärksamhet. "
            "När du är ledig och barfota ute – passa på att träna rörlighet och cirkulation "
            "på ett enkelt och naturligt sätt.\n\n"
            "## Ge fötterna sommarträning\n"
            "✔ Gå barfota i gräs, sand eller på en filt och låt fötterna känna olika underlag.\n"
            "✔ Böj och sträck tårna flera gånger.\n"
            "✔ Försök att greppa en handduk eller lite gräs med tårna och släpp igen.\n\n"
            "Det hjälper till att väcka små muskler i fötterna och hålla dem rörliga.\n\n"
            "## Ge händerna lite kärlek\n"
            "✔ Låt tummen möta ett finger i taget – pekfinger, långfinger, ringfinger och lillfinger.\n"
            "✔ Sträck ut fingrarna och slappna av.\n\n"
            "En liten stund varje dag kan göra stor skillnad för hur händerna känns.\n\n"
            "## Mitt tips:\n"
            "Gör dina rörelser när du sitter på stranden, i trädgården eller på balkongen. "
            "Några minuter av egen tid kan vara en enkel väg till mer välmående."
        )
        season_defaults = [
            (2, "Februari–april", "Vårda torra vinterhänder och fötter med värmande behandlingar."),
            (5, "Maj – Förbered dig för sommaren!", "Mjuka upp fötter inför öppna skor och sommarvärme."),
            (6, "Juni", "Spa-pedikyr och värmande manikyr håller händer och fötter i form."),
            (
                7,
                "Juli – Ge händer och fötter lite extra sommaromsorg",
                july_body,
            ),
            (
                8,
                "Augusti – Ge händer och fötter lite extra sommaromsorg",
                july_body,
            ),
            (9, "September", "Bygg upp fuktbarriären inför svalare dagar."),
            (10, "Oktober", "Värmande paraffin mot stelhet och torrhet."),
            (11, "November", "Extra omsorg när kylan tar ut sin rätt."),
            (12, "December", "Ge dig själv egentid mitt i julruschen."),
        ]
        for month, title, body in season_defaults:
            SeasonTip.objects.update_or_create(
                month=month,
                defaults={"title": title, "body": body, "is_visible": True},
            )

        services = [
            ("Evig Lycka – Spa-pedikyr", 60, 425, "Avkopplande spa-pedikyr med nagelvård och vårdande kräm."),
            ("Gyllene Beröring – Värmande paraffinpedikyr", 75, 499, "Spa-pedikyr med värmande paraffin."),
            ("Lugnande Händer – Manikyr med lack", 45, 375, "Manikyr med nagelbandsvård, massage och lack."),
            ("Ren Omsorg – Värmande paraffinmanikyr", 60, 499, "Värmande paraffinmanikyr med handmassage."),
            ("Kunglig Avkoppling – Kombo behandling", 120, 800, "Spa-pedikyr och manikyr med paraffin och massage."),
            ("Lugnande Stund – Hand- eller fotmassage", 30, 250, "Massage med fokus på avkoppling."),
        ]
        for order, (name, mins, price, desc) in enumerate(services, start=1):
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
        # Deactivate legacy service names if they remain from older seeds.
        Service.objects.filter(
            slug__in=["spa-pedikyr", "varmande-manikyr", "paraffinbehandling"]
        ).update(is_active=False)

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
