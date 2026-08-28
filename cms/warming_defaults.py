# cms/warming_defaults.py — default copy for SitePage key=warming

"""Default Värmande behandlingar page text.

Live edits: Admin → CMS → Sidor → Värmande behandlingar
(title, subtitle, body, knappar). Seed overwrites only with --force.
"""

from cms.text_format import BOLD_MARKUP_HINT  # noqa: F401 — docs hint for editors

WARMING_TITLE = "Värmande behandlingar"
WARMING_SUBTITLE = "Värme, mjukhet och vård – året om"
# Adjust: button labels — editable in Admin → Sidor → Värmande behandlingar
WARMING_CTA_PRIMARY = "Boka"
WARMING_CTA_SECONDARY = "Se värmande behandlingar & priser"

# Adjust: ## headings and • lists; **bold** supported on the public page
WARMING_BODY = (
    "Värmande behandlingar är en av EGentids specialiteter. En varm och skön stund för "
    "händer och fötter där värme, vårdande produkter och massage kombineras.\n\n"
    "## Värmande paraffin\n"
    "Paraffinet omsluter händer eller fötter med en behaglig värme och bildar ett mjukt "
    "lager runt huden. Värmen kan bidra till ökad lokal blodcirkulation och hjälper till "
    "att mjuka upp huden.\n\n"
    "När huden omsluts av paraffinet minskar avdunstningen, vilket hjälper huden att "
    "behålla sin fukt. Efter behandlingen kan huden kännas mjukare, smidigare och mer "
    "återfuktad.\n\n"
    "Värmen kan också kännas extra skön när händer, fötter eller leder känns stela.\n\n"
    "Ett härligt komplement för dig som:\n"
    "• har torra händer eller fötter\n"
    "• lätt fryser om händer och fötter\n"
    "• uppskattar värme vid stelhet\n"
    "• vill ge huden extra mjukgörande vård\n"
    "• vill njuta av en varm och avkopplande behandling\n\n"
    "Värmande paraffin är ett komplement till behandlingen och ersätter inte medicinsk behandling.\n\n"
    "## När naglarna behöver extra omsorg\n"
    "Värme och vårdande produkter kan också vara ett fint komplement för tunna, sköra "
    "eller flisiga naglar.\n\n"
    "Det passar även dig som nyligen haft nagelförlängning eller nagelförstärkning och "
    "vill ge naglarna lite extra vård och återhämtning innan nästa behandling.\n\n"
    "## Kokosolja – mild och vårdande\n"
    "Kokosolja är rik på fettsyror och hjälper till att mjukgöra och vårda torr hud. "
    "Den passar bra även för känslig hud och lämnar en mjuk och behaglig känsla.\n\n"
    "I EGentid används den som en del av den vårdande behandlingen och vid massage.\n\n"
    "## Sötmandelolja – silkeslen och lyxig\n"
    "Sötmandelolja innehåller bland annat omättade fettsyror och vitamin E. Den hjälper "
    "till att mjukgöra huden, bevara fukt och göra huden smidig.\n\n"
    "Den silkeslena känslan gör den särskilt härlig vid massage av händer, fötter och "
    "vader – en liten extra känsla av lyx i behandlingen.\n\n"
    "## Värme som passar året om\n"
    "Värmande behandlingar är inte bara för kalla vinterdagar. Händer och fötter kan "
    "behöva extra mjukgörande vård under hela året – efter vinterns kyla, sommarens "
    "barfotadagar eller när huden helt enkelt känns torr och behöver lite mer omsorg.\n\n"
    "**Värme. Vård. Massage. Egentid.**\n\n"
    "Vill du uppleva värmen själv?"
)

# Previous short seed body — used so deploy can upgrade once without --force
WARMING_BODY_LEGACY = (
    "Ökar blodcirkulationen.\n\n"
    "Mjukar upp stela och ömma leder.\n\n"
    "Lindrar torr hud och sprickor.\n\n"
    "Perfekt vid reumatism, artrit och ledvärk."
)
