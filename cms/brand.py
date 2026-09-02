# cms/brand.py — public brand name and staff inbox; rewrite leftover CMS text

"""Canonical brand string and contact email used in titles, seed, and snapshot.

Adjust: change BRAND_NAME or CONTACT_EMAIL here if the public name or inbox changes.
"""

from __future__ import annotations

BRAND_NAME = "EGentid Spa & Service"
BRAND_NAME_LEGACY = "EGentid Spa & Resurs"

# Adjust: staff inbox for footer, contact form, and new-booking notices.
CONTACT_EMAIL = "egentidspaservice@gmail.com"
CONTACT_EMAIL_LEGACY = frozenset(
    {
        "info@egentidspaservice.se",
        "info@egentidsparesurs.se",
    }
)

# CharField/TextField names that may still contain the old brand.
_PAGE_TEXT_FIELDS = (
    "title",
    "subtitle",
    "body",
    "cta_primary",
    "cta_secondary",
    "meta_title",
    "meta_description",
)
_BLOCK_TEXT_FIELDS = ("title", "body")
_SETTINGS_TEXT_FIELDS = (
    "site_name",
    "tagline",
    "footer_text",
    "default_meta_description",
    "address",
)


def is_legacy_contact_email(value: str) -> bool:
    """True for old info@ addresses that should now go to CONTACT_EMAIL."""
    return (value or "").strip().lower() in CONTACT_EMAIL_LEGACY


def with_current_brand(text: str) -> str:
    """Replace leftover Spa & Resurs wording for display (titles, meta)."""
    if not text:
        return text
    return text.replace(BRAND_NAME_LEGACY, BRAND_NAME)


def document_title(seo_title: str, site_name: str) -> str:
    """Browser tab title: SEO text plus site name only when the name is missing."""
    seo = with_current_brand((seo_title or "").strip())
    name = with_current_brand((site_name or "").strip()) or BRAND_NAME
    if not seo:
        return name
    if name.casefold() in seo.casefold():
        return seo
    return f"{seo} – {name}"


def replace_legacy_brand_in_db() -> int:
    """Rewrite leftover brand text and old info@ inbox in CMS. Returns how many rows changed.

    Safe to run on every deploy; skips rows that already use the current name/email.
    """
    from cms.models import ContentBlock, SitePage, SiteSettings

    changed = 0
    settings = SiteSettings.load()
    settings_fields = []
    for field in _SETTINGS_TEXT_FIELDS:
        raw = getattr(settings, field, "") or ""
        updated = with_current_brand(raw)
        if updated != raw:
            setattr(settings, field, updated)
            settings_fields.append(field)
    if is_legacy_contact_email(settings.email or ""):
        settings.email = CONTACT_EMAIL
        settings_fields.append("email")
    if settings_fields:
        settings.save(update_fields=settings_fields)
        changed += 1

    for page in SitePage.objects.all():
        fields = []
        for field in _PAGE_TEXT_FIELDS:
            raw = getattr(page, field, "") or ""
            updated = with_current_brand(raw)
            if updated != raw:
                setattr(page, field, updated)
                fields.append(field)
        if fields:
            page.save(update_fields=fields)
            changed += 1

    for block in ContentBlock.objects.all():
        fields = []
        for field in _BLOCK_TEXT_FIELDS:
            raw = getattr(block, field, "") or ""
            updated = with_current_brand(raw)
            if updated != raw:
                setattr(block, field, updated)
                fields.append(field)
        if fields:
            block.save(update_fields=fields)
            changed += 1

    return changed
