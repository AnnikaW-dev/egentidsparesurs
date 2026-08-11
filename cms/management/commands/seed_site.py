"""Seed default pages, services, schedule, and copy from the WordPress site."""

from datetime import date, time, timedelta
from pathlib import Path

from django.core.files import File
from django.core.management.base import BaseCommand
from django.utils.text import slugify

from booking.models import Service, WeeklyAvailability, generate_slots_for_range
from cms.models import ContentBlock, GalleryImage, SeasonTip, SitePage, SiteSettings


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
                "subtitle": "Fotvård, handvård och oljor anpassade efter din hud.",
                "body": (
                    "Här hittar du behandlingar för händer och fötter – från spa-pedikyr "
                    "till paraffin och närande oljor. Välj det som passar dig, eller "
                    "fråga mig så hjälper jag dig hitta rätt."
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
                "subtitle": "Aktuella priser för behandlingar.",
                "body": "Alla tider bokas online. Priserna kan justeras – hör av dig om du har frågor.",
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
        ContentBlock.objects.create(
            page=treatments,
            title="Paraffin",
            body=(
                "Passar dig som:\n"
                "Har torra händer och fötter\n"
                "Har värk i leder och muskler\n"
                "Vill ha en avslappnande lyxig behandling"
            ),
            sort_order=1,
        )
        ContentBlock.objects.create(
            page=treatments,
            title="Olja nr 1 – För känslig och mycket torr hud (från 5 år)",
            body=(
                "Återfuktar på djupet och stärker hudens skyddsbarriär.\n"
                "Lugnar eksem och irriterad hud.\n"
                "Perfekt för känslig hud och extra torr hud.\n"
                "Passar både barn och vuxna."
            ),
            sort_order=2,
        )
        ContentBlock.objects.create(
            page=treatments,
            title="Olja nr 2 – Lyxig & rogivande för normal hud",
            body=(
                "Näringsboost för huden med extra lyster.\n"
                "Stärker elasticitet och stimulerar cellförnyelse.\n"
                "Lyxig och rogivande behandling med härliga dofter.\n\n"
                "Innehåll: Vitamin E, Vitamin A, Omega-9, Omega-6 och Zink."
            ),
            sort_order=3,
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

        # Full monthly tip bodies use ### headings and ✔ items (see SeasonTip.body_blocks).
        # Adjust: edit each month in Admin → Säsongstips.
        summer_care_body = (
            "Sommaren är en perfekt tid att ge händer och fötter lite extra uppmärksamhet. "
            "När du är ledig och barfota ute – passa på att träna rörlighet och cirkulation "
            "på ett enkelt och naturligt sätt.\n\n"
            "### Ge fötterna sommarträning\n"
            "✔ Gå barfota i gräs, sand eller på en filt och låt fötterna känna olika underlag.\n"
            "✔ Böj och sträck tårna flera gånger.\n"
            "✔ Försök att greppa en handduk eller lite gräs med tårna och släpp igen.\n\n"
            "Det hjälper till att väcka små muskler i fötterna och hålla dem rörliga.\n\n"
            "### Ge händerna lite kärlek\n"
            "✔ Låt tummen möta ett finger i taget – pekfinger, långfinger, ringfinger och lillfinger.\n"
            "✔ Sträck ut fingrarna och slappna av.\n\n"
            "En liten stund varje dag kan göra stor skillnad för hur händerna känns.\n\n"
            "### Mitt tips:\n"
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
                summer_care_body,
            ),
            (
                8,
                "Augusti – Ge händer och fötter lite extra sommaromsorg",
                summer_care_body,
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
            ("Spa-pedikyr", 75, 695, "Avkopplande fotvård som återfuktar och mjukar upp."),
            ("Värmande manikyr", 60, 595, "Handvård med massage och närande produkter."),
            ("Paraffinbehandling", 45, 450, "Värmande paraffin för torra händer eller fötter."),
        ]
        for name, mins, price, desc in services:
            Service.objects.update_or_create(
                slug=slugify(name),
                defaults={
                    "name": name,
                    "duration_minutes": mins,
                    "price_sek": price,
                    "description": desc,
                    "is_active": True,
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
