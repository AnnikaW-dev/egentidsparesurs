# cms/brand.py — public brand name; rewrite leftover “Resurs” in CMS/SEO text

"""Canonical brand string used in titles, seed, and snapshot.

Adjust: change BRAND_NAME here if the public name changes again.
"""

from __future__ import annotations

BRAND_NAME = "EGentid Spa & Service"
BRAND_NAME_LEGACY = "EGentid Spa & Resurs"

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
    """Rewrite EGentid Spa & Resurs → Service in CMS rows. Returns how many rows changed.

    Safe to run on every deploy; skips rows that already use the current name.
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
