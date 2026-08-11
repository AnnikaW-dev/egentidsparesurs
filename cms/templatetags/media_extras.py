"""Template helpers for optimized media delivery (WebP)."""

from pathlib import Path

from django import template
from django.conf import settings

register = template.Library()


def _media_path_for_url(url: str) -> Path | None:
    """Map a /media/... URL to a file under MEDIA_ROOT, if possible."""
    prefix = settings.MEDIA_URL or "/media/"
    if not url.startswith(prefix):
        return None
    rel = url[len(prefix) :].lstrip("/")
    if not rel or ".." in rel:
        return None
    return Path(settings.MEDIA_ROOT) / rel


@register.filter
def as_webp(file_or_url):
    """Return a .webp URL when a companion file exists; otherwise the original.

    Adjust: run scripts/optimize_images.py after adding JPEGs under static/img or media/.
    """
    if not file_or_url:
        return ""
    url = file_or_url.url if hasattr(file_or_url, "url") else str(file_or_url)
    lower = url.lower()
    webp_url = None
    for ext in (".jpeg", ".jpg", ".png"):
        if lower.endswith(ext):
            webp_url = url[: -len(ext)] + ".webp"
            break
    if not webp_url:
        return url

    # Prefer WebP only when the file is actually on disk (avoids broken <source>).
    path = _media_path_for_url(webp_url)
    if path is not None and path.is_file():
        return webp_url

    # Static files under STATICFILES_DIRS (e.g. /static/img/logo.webp).
    static_prefix = settings.STATIC_URL or "/static/"
    if webp_url.startswith(static_prefix):
        rel = webp_url[len(static_prefix) :].lstrip("/")
        for root in getattr(settings, "STATICFILES_DIRS", []):
            candidate = Path(root) / rel
            if candidate.is_file():
                return webp_url

    return url
