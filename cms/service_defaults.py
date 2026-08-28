# cms/service_defaults.py — default copy for SitePage key=service

"""Default Service page text.

Live edits: Admin → CMS → Sidor → Service
(title, subtitle, body, knapp). Seed overwrites only with --force or one-time legacy upgrade.
"""

from cms.text_format import BOLD_MARKUP_HINT  # noqa: F401 — docs hint for editors

SERVICE_TITLE = "Service"
SERVICE_SUBTITLE = "**Mer än behandling – hjälp som sparar din tid och energi.**"
SERVICE_CTA_PRIMARY = "Kontakta mig"

# Adjust: **bold** for emphasis as on the public page
SERVICE_BODY = (
    "Behöver du avlastning med uppgifter som tar tid och kraft från det du egentligen "
    "vill fokusera på?\n\n"
    "Jag kan hjälpa till med exempelvis **administration, företagskontakt, mötesbokning, "
    "uppföljning och andra praktiska eller serviceinriktade uppgifter.**\n\n"
    "Behöver du hjälp med något annat? **Hör gärna av dig ändå.** Vi kan prata om vad du "
    "behöver och se om jag kan hjälpa dig."
)

SERVICE_BODY_LEGACY = (
    "Behöver du avlastning med administrativa uppgifter eller en lugn stund "
    "för att prata igenom vad som tar tid och kraft i vardagen?\n\n"
    "Här kan du släppa stressen och låta mig ta hand om det som ger dig mer "
    "egentid. Hör av dig via kontaktformuläret så hittar vi en lösning "
    "tillsammans."
)
