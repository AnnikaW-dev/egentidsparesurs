# cms/a11y.py — shared alt-text and admin copy for EU/WCAG 2.1 AA

"""Keep image alt text and admin hints in one place when editors change CMS content."""

from cms.text_format import _BOLD_RE

# Adjust: fallback when caption, title, and context title are all empty
DEFAULT_IMAGE_ALT = "Bild från salongen och behandlingarna"

A11Y_GALLERY_CAPTION_HELP = (
    "Bildtext för skärmläsare (alt-text). Används på Galleri och när bilden "
    "väljes på sidor/innehållsblock. Beskriv kort vad som syns, t.ex. "
    "”Paraffinbad för händer”. Tom bildtext → titeln används i stället."
)

A11Y_PAGE_IMAGE_HELP = (
    "Tillgänglighet: välj Hero från galleri när du kan — då används bildtexten "
    "från Galleribilder. Extra hero-rader (Hem / Behandlingar) blir ett bildspel. "
    "Egen uppladdning får sidans titel som alt-text."
)

A11Y_BLOCK_IMAGE_HELP = (
    "Tillgänglighet: välj Bild från galleri när du kan. Annars används "
    "blockets titel som alt-text för egen uppladdning."
)


def plain_cms_text(value: str) -> str:
    """Strip **bold** markup for alt text and plain-language checks."""
    return _BOLD_RE.sub(r"\1", str(value or "")).strip()


def resolve_image_alt(*, caption: str = "", title: str = "", fallback: str = "") -> str:
    """Pick alt text: caption → title → fallback → site default."""
    for candidate in (caption, title, fallback):
        text = plain_cms_text(candidate)
        if text:
            return text
    return DEFAULT_IMAGE_ALT
