"""XML sitemap for public pages, including gallery images.

Locations use the canonical host from cms.seo (not the Render hostname).
"""

from urllib.parse import urlparse

from django.contrib.sitemaps import Sitemap
from django.http import HttpRequest
from django.urls import reverse

from config.hosts import PRODUCTION_HOSTS

# Adjust: how many gallery photos to list under /galleri/ in the sitemap.
_MAX_GALLERY_IMAGES = 50


class StaticViewSitemap(Sitemap):
    """Public marketing and booking URLs — exclude admin and dashboard."""

    changefreq = "weekly"
    protocol = None

    # (url name, priority) — Adjust priorities if a page becomes more important.
    PAGES = (
        ("home", 1.0),
        ("about", 0.8),
        ("treatments", 0.9),
        ("warming", 0.8),
        ("seasons", 0.6),
        ("gallery", 0.5),
        ("booking", 0.9),
        ("contact", 0.7),
        ("service", 0.7),
        ("accessibility", 0.3),
        ("privacy", 0.3),
    )
    # url name → SitePage.key for lastmod. Static legal pages have no CMS row.
    PAGE_KEYS = {
        "home": "home",
        "about": "salon",
        "treatments": "treatments",
        "warming": "warming",
        "seasons": "seasons",
        "gallery": "gallery",
        "booking": "booking",
        "contact": "contact",
        "service": "service",
    }

    def items(self):
        """Skip a CMS page whose Is published box is unchecked."""
        from cms.models import SitePage

        unpublished = set(
            SitePage.objects.filter(is_published=False).values_list("key", flat=True)
        )
        names = []
        for name, _priority in self.PAGES:
            key = self.PAGE_KEYS.get(name)
            if key and key in unpublished:
                continue
            names.append(name)
        return names

    def location(self, item):
        return reverse(item)

    def priority(self, item):
        return dict(self.PAGES)[item]

    def lastmod(self, item):
        """CMS updated_at so Google can skip unchanged pages."""
        from cms.models import SitePage

        key = self.PAGE_KEYS.get(item)
        if not key:
            return None
        page = SitePage.objects.filter(key=key).only("updated_at").first()
        return page.updated_at if page else None

    def get_urls(self, page=1, site=None, protocol=None):
        origin, protocol, site = _canonical_site(site, protocol)
        urls = super().get_urls(page=page, site=site, protocol=protocol)
        images = _gallery_images(origin)
        for url in urls:
            url["images"] = images if url["item"] == "gallery" else []
        return urls


def _canonical_site(site, protocol):
    """Rewrite sitemap host to the public origin."""
    from cms.models import SiteSettings
    from cms.seo import public_base_url

    domain = getattr(site, "domain", "") or "localhost"
    request = HttpRequest()
    request.META["HTTP_HOST"] = domain
    host = domain.split(":")[0].lower()
    request.META["SERVER_NAME"] = host
    scheme = protocol or "http"
    if host in PRODUCTION_HOSTS or host.endswith(".onrender.com"):
        scheme = "https"
    request.META["wsgi.url_scheme"] = scheme
    request.META["SERVER_PORT"] = "443" if scheme == "https" else "80"
    request.path = "/"
    request.method = "GET"
    origin = public_base_url(request, SiteSettings.load())
    parsed = urlparse(origin)

    class _Domain:
        pass

    fake = _Domain()
    fake.domain = parsed.netloc
    return origin, parsed.scheme or scheme, fake


def _gallery_images(origin: str):
    """Absolute image URLs for the gallery sitemap extension."""
    from cms.a11y import plain_cms_text
    from cms.models import GalleryImage

    rows = []
    images = GalleryImage.objects.filter(is_visible=True).exclude(image="")
    for image in images:
        try:
            path = image.image.url
        except Exception:
            continue
        if path.startswith("http://") or path.startswith("https://"):
            loc = path
        else:
            loc = origin.rstrip("/") + path
        caption = plain_cms_text(image.caption or image.title)
        title = plain_cms_text(image.title)
        rows.append({"loc": loc, "caption": caption, "title": title})
        if len(rows) >= _MAX_GALLERY_IMAGES:
            break
    return rows
