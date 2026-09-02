# cms/templatetags/cms_extras.py — CMS text filters (bold markup, etc.)

"""Template filters for CMS-authored text."""

from django import template

from cms.brand import document_title as compose_document_title
from cms.text_format import format_inline_markup

register = template.Library()


@register.filter(name="cms_richtext")
def cms_richtext(value):
    """Render admin text with **bold** → <strong>, HTML-escaped otherwise.

    Adjust: use **ord** in any CMS field shown through this filter.
    """
    return format_inline_markup(value)


@register.filter(name="cms_richtext_br")
def cms_richtext_br(value):
    """Like cms_richtext, but also converts newlines to <br>."""
    return format_inline_markup(value, newlines=True)


@register.filter(name="document_title")
def document_title_filter(page, site_name):
    """Browser <title> for a CMS page: current brand, no duplicated site name."""
    if page is None:
        return compose_document_title("", site_name or "")
    return page.document_title(site_name or "")
