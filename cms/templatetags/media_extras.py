"""Template helpers for optimized media delivery (WebP)."""

from django import template

register = template.Library()


@register.filter
def as_webp(file_or_url):
    """Return a .webp URL for a FileField/url string when the source is jpg/png.

    Adjust: ensure scripts/optimize_images.py (or upload pipeline) creates the .webp file.
    """
    if not file_or_url:
        return ""
    url = file_or_url.url if hasattr(file_or_url, "url") else str(file_or_url)
    lower = url.lower()
    for ext in (".jpeg", ".jpg", ".png"):
        if lower.endswith(ext):
            return url[: -len(ext)] + ".webp"
    return url
