# cms/salon_defaults.py — default copy for SitePage key=salon (Om)

"""Default Om page text.

Live edits: Admin → CMS → Sidor → Om
(title, subtitle, body). Seed overwrites only with --force or one-time legacy upgrade.
"""

from cms.text_format import BOLD_MARKUP_HINT  # noqa: F401 — docs hint for editors

SALON_TITLE = "Min salong – en liten plats för egentid"
SALON_SUBTITLE = ""

# Adjust: ## for underrubrik; **bold** supported on the public page
SALON_BODY = (
    "Välkommen till en liten personlig salong i Linköping, inredd i varma beige och bruna "
    "toner med naturliga detaljer.\n\n"
    "Salongen ligger på nedervåningen i mitt hem och har en egen ingång. Här finns en lugn "
    "behandlingsmiljö och en liten soffhörna där du kan slå dig ner före eller efter din "
    "behandling.\n\n"
    "## Hitta hit\n"
    "Du hittar EGentid i Berga, på gatan som leder in mot Ånestadsskolan. Salongen ligger "
    "precis i hörnet när du svänger in på gatan, strax ovanför INGO-macken.\n\n"
    "En liten, personlig plats där du får landa en stund."
)

# Personlig presentation under Boka — photo left, text right; Admin → Sidor → Om → Innehållsblock
SALON_PROFILE_TITLE = "En stund som bara är din."
SALON_PROFILE_BODY = (
    "Jag heter Emma och står bakom EGentid Spa & Resurs.\n\n"
    "Jag tror att vi ibland behöver stanna upp och ge oss själva lite mer tid – men också "
    "att det kan vara skönt att få hjälp med sådant som tar tid och energi i vardagen.\n\n"
    "Därför har jag skapat EGentid med två delar: spa och återhämtning samt service och "
    "avlastning.\n\n"
    "I salongen får du en personlig stund med fokus på händer, fötter, värme och massage. "
    "Genom EGentid Service kan jag även hjälpa privatpersoner och företag med uppgifter som "
    "behöver göras, men som du kanske inte själv hinner med.\n\n"
    "**Personligt, flexibelt och med omtanke.**\n\n"
    "Välkommen till EGentid."
)

# Previous seed copy — used so deploy can upgrade once without --force
SALON_TITLE_LEGACY = "Min salong – En plats för avkoppling och fokus"
SALON_BODY_LEGACY = (
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
)
