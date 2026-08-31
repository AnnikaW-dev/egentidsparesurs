"""SEO helpers: absolute URLs and JSON-LD for LocalBusiness."""

import json
import os

from django.urls import reverse


def absolute_url(request, path=None):
    """Build an absolute URL for path (or current request path)."""
    if path is None:
        path = request.path
    return request.build_absolute_uri(path)


def public_base_url(request, site):
    """Canonical site origin for JSON-LD and sitemap hints.

    Prefer CMS public_site_url, then PUBLIC_SITE_URL / Render URL, then the request.
    """
    stored = (getattr(site, "public_site_url", "") or "").strip().rstrip("/")
    if stored:
        return stored
    for name in ("PUBLIC_SITE_URL", "RENDER_EXTERNAL_URL"):
        raw = os.environ.get(name, "").strip().rstrip("/")
        if raw:
            return raw
    return absolute_url(request, reverse("home")).rstrip("/")


def local_business_json_ld(request, site):
    """
    Schema.org BeautySalon / LocalBusiness JSON-LD for rich results.

    Adjust: fill phone/address/public_site_url in SiteSettings admin.
    """
    data = {
        "@context": "https://schema.org",
        "@type": "BeautySalon",
        "name": site.site_name,
        "description": site.default_meta_description or site.tagline,
        "url": public_base_url(request, site),
        "image": absolute_url(request, site.logo.url) if site.logo else None,
        "email": site.email or None,
        "telephone": site.phone or None,
        "address": {
            "@type": "PostalAddress",
            "streetAddress": site.address or None,
            "addressCountry": "SE",
        },
        "sameAs": [u for u in (site.facebook_url, site.linkedin_url) if u],
        "makesOffer": {
            "@type": "Offer",
            "itemOffered": {
                "@type": "Service",
                "name": "Fotvård och handvård",
                "description": "Spa-pedikyr, värmande manikyr och paraffinbehandlingar.",
            },
        },
    }
    # Drop empty values for cleaner JSON-LD.
    def clean(obj):
        if isinstance(obj, dict):
            return {k: clean(v) for k, v in obj.items() if v not in (None, "", [], {})}
        if isinstance(obj, list):
            return [clean(v) for v in obj if v not in (None, "", [], {})]
        return obj

    return json.dumps(clean(data), ensure_ascii=False)
