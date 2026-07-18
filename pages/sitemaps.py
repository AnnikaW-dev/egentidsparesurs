"""XML sitemaps for public pages (SEO)."""

from django.contrib.sitemaps import Sitemap
from django.urls import reverse


class StaticViewSitemap(Sitemap):
    """Public marketing and booking URLs — exclude admin/dashboard."""

    changefreq = "weekly"
    # Use the request scheme in development (http) and production (https).
    protocol = None

    # (url name, priority) — Adjust priorities if a page becomes more important.
    PAGES = (
        ("home", 1.0),
        ("salon", 0.8),
        ("treatments", 0.9),
        ("seasons", 0.6),
        ("gallery", 0.5),
        ("booking", 0.9),
        ("contact", 0.7),
        ("accessibility", 0.3),
    )

    def items(self):
        return list(self.PAGES)

    def location(self, item):
        return reverse(item[0])

    def priority(self, item):
        return item[1]
