"""SEO helpers: canonical URLs, JSON-LD, and stock meta descriptions.

Canonical host is the CMS public URL, then PUBLIC_SITE_URL, then
https://egentidspaservice.se when the request is on that domain or Render.
Localhost keeps the request host. Adjust city and snippet text below.
"""

import json
import os
import re
from urllib.parse import urlparse

from django.urls import reverse

from config.hosts import PRODUCTION_HOSTS

# Adjust: city in structured data when Kontakt has no postort. Matches the Om page.
DEFAULT_LOCALITY = "Linköping"

# Adjust: default search snippet when a page has no meta description (max 160 chars).
DEFAULT_META_DESCRIPTION = (
    "Fotvård och spa-pedikyr i Linköping. Värmande manikyr och paraffin. "
    "Boka tid hos EGentid Spa & Service."
)
# Seed replaces only these stock sentences, never a description written in admin.
DEFAULT_META_DESCRIPTION_PREVIOUS = (
    "Fotvård, spa-pedikyr och värmande manikyr. Boka egentid hos EGentid Spa & Service.",
    "Fotvård, spa-pedikyr och värmande manikyr. Boka egentid hos EGentid Spa & Resurs.",
)

TREATMENTS_META_DESCRIPTION = (
    "Priser för fotvård, handvård och massage i Linköping. "
    "Boka hos EGentid Spa & Service."
)
TREATMENTS_META_DESCRIPTION_PREVIOUS = (
    "Fotvård, handvård och massage med priser hos EGentid Spa & Service.",
    "Fotvård, handvård och massage med priser hos EGentid Spa & Resurs.",
)

# url name → breadcrumb label. Home is included but not shown as a trail.
PUBLIC_PAGES = {
    "home": "Hem",
    "about": "Om",
    "treatments": "Behandlingar och priser",
    "warming": "Värmande behandlingar",
    "seasons": "Året runt",
    "gallery": "Galleri",
    "booking": "Boka tid",
    "contact": "Kontakt",
    "service": "Service",
    "accessibility": "Tillgänglighet",
    "privacy": "Integritet",
}

_SCHEMA_DAYS = (
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday",
)
_POSTAL_RE = re.compile(r"\b(\d{3})\s?(\d{2})\b")
_PRICE_RE = re.compile(r"(\d+)\s*kr", re.IGNORECASE)
# Adjust: cap treatment offers embedded in JSON-LD.
_MAX_OFFERS = 30


def upgrade_stock_seo() -> int:
    """Replace leftover stock snippets and non-canonical hosts.

    Safe on every deploy. Skips a meta description an editor has customized.
    Returns how many rows were saved.
    """
    from cms.models import SitePage, SiteSettings

    changed = 0
    settings = SiteSettings.load()
    fields = []
    if (settings.default_meta_description or "").strip() in DEFAULT_META_DESCRIPTION_PREVIOUS:
        settings.default_meta_description = DEFAULT_META_DESCRIPTION
        fields.append("default_meta_description")
    stored = (settings.public_site_url or "").strip().rstrip("/")
    lowered = stored.lower()
    if stored and ("onrender.com" in lowered or "egentidsparesurs" in lowered):
        settings.public_site_url = _usable_origin(
            os.environ.get("PUBLIC_SITE_URL", "")
        ) or ("https://" + PRODUCTION_HOSTS[0])
        fields.append("public_site_url")
    if fields:
        settings.save(update_fields=fields)
        changed += 1
    treatments = SitePage.objects.filter(key=SitePage.PageKey.TREATMENTS).first()
    if (
        treatments
        and (treatments.meta_description or "").strip() in TREATMENTS_META_DESCRIPTION_PREVIOUS
    ):
        treatments.meta_description = TREATMENTS_META_DESCRIPTION
        treatments.save(update_fields=["meta_description"])
        changed += 1
    return changed


def dumps_ld(data) -> str:
    """JSON-LD safe to embed in a script tag."""
    return json.dumps(data, ensure_ascii=False).replace("<", "\\u003c")


def _clean(obj):
    """Drop empty values so Google does not see blank address fields."""
    if isinstance(obj, dict):
        return {k: _clean(v) for k, v in obj.items() if v not in (None, "", [], {})}
    if isinstance(obj, list):
        return [_clean(v) for v in obj if v not in (None, "", [], {})]
    return obj


def _request_host(request) -> str:
    """Hostname without calling get_host(), which rejects unknown hosts."""
    meta = getattr(request, "META", {}) or {}
    raw = meta.get("HTTP_HOST") or meta.get("SERVER_NAME") or ""
    return raw.split(":")[0].lower().strip()


def _usable_origin(url: str) -> str:
    """Return url without a trailing slash, or empty for Render/legacy hosts."""
    raw = (url or "").strip().rstrip("/")
    if not raw:
        return ""
    if "://" not in raw:
        raw = "https://" + raw
    host = (urlparse(raw).hostname or "").lower()
    if not host or host.endswith(".onrender.com") or "egentidsparesurs" in host:
        return ""
    return raw


def public_base_url(request, site) -> str:
    """Canonical site origin, no trailing slash.

    Prefer CMS public_site_url, then PUBLIC_SITE_URL. The Render hostname is
    never canonical. www and *.onrender.com collapse to the apex production domain.
    """
    stored = _usable_origin(getattr(site, "public_site_url", "") or "")
    if stored:
        return stored
    env = _usable_origin(os.environ.get("PUBLIC_SITE_URL", ""))
    if env:
        return env
    host = _request_host(request)
    if host in PRODUCTION_HOSTS or host.endswith(".onrender.com"):
        return "https://" + PRODUCTION_HOSTS[0]
    return absolute_url(request, reverse("home")).rstrip("/")


def absolute_url(request, path=None) -> str:
    """Build an absolute URL for path (or the current request path) on this host."""
    if path is None:
        path = request.path
    return request.build_absolute_uri(path)


def canonical_url(request, site, path=None) -> str:
    """Absolute canonical URL: public origin + path, query string removed."""
    if path is None:
        path = getattr(request, "path", "/") or "/"
    path = path.split("?", 1)[0]
    if not path.startswith("/"):
        path = "/" + path
    return public_base_url(request, site).rstrip("/") + path


def public_absolute_url(request, site, path: str) -> str:
    """Absolute URL for a media or page path on the canonical host."""
    if not path:
        return ""
    if path.startswith("http://") or path.startswith("https://"):
        return path
    if not path.startswith("/"):
        path = "/" + path
    return public_base_url(request, site).rstrip("/") + path


def schema_telephone(site) -> str:
    """E.164-style phone for JSON-LD. Display text stays in site.phone."""
    tel = site.phone_tel() if hasattr(site, "phone_tel") else ""
    if not tel:
        return ""
    if tel.startswith("+"):
        return tel
    if tel.startswith("0"):
        return "+46" + tel[1:]
    return tel


def postal_address(text: str) -> dict:
    """PostalAddress for JSON-LD.

    Street is included only when the text has a house number. The entrance
    note in the footer is not a street address. City defaults to Linköping.
    """
    from cms.a11y import plain_cms_text

    raw = " ".join(plain_cms_text(text).replace("\n", " ").split())
    data = {
        "@type": "PostalAddress",
        "addressLocality": DEFAULT_LOCALITY,
        "addressCountry": "SE",
    }
    match = _POSTAL_RE.search(raw)
    if match:
        data["postalCode"] = f"{match.group(1)} {match.group(2)}"
        before = raw[: match.start()].strip(" ,")
        after = raw[match.end() :].strip(" ,")
        if before and re.search(r"\d", before):
            data["streetAddress"] = before
        if after:
            data["addressLocality"] = after.split(",")[0].strip()
    if data["addressLocality"].casefold() == DEFAULT_LOCALITY.casefold():
        data["addressRegion"] = "Östergötland"
    return data


def _opening_hours():
    """OpeningHoursSpecification rows from the booking week schedule."""
    from booking.models import WeeklyAvailability

    specs = []
    rules = WeeklyAvailability.objects.filter(is_active=True).order_by(
        "weekday", "start_time"
    )
    for rule in rules:
        day = "https://schema.org/" + _SCHEMA_DAYS[rule.weekday]
        if rule.lunch_start and rule.lunch_end:
            windows = (
                (rule.start_time, rule.lunch_start),
                (rule.lunch_end, rule.end_time),
            )
        else:
            windows = ((rule.start_time, rule.end_time),)
        for opens, closes in windows:
            specs.append(
                {
                    "@type": "OpeningHoursSpecification",
                    "dayOfWeek": day,
                    "opens": opens.strftime("%H:%M"),
                    "closes": closes.strftime("%H:%M"),
                }
            )
    return specs


def _treatment_offers(request, site):
    """Offers from visible Behandlingar blocks, else active booking services."""
    from cms.a11y import plain_cms_text
    from cms.models import ContentBlock, SitePage

    origin = public_base_url(request, site).rstrip("/")
    treatments = origin + reverse("treatments")
    offers = []
    blocks = ContentBlock.objects.filter(
        page__key=SitePage.PageKey.TREATMENTS,
        page__is_published=True,
        is_visible=True,
    ).order_by("sort_order", "id")
    for block in blocks:
        if block.is_category_heading():
            continue
        name = plain_cms_text(block.title)
        if not name:
            continue
        item = {
            "@type": "Service",
            "name": name,
            "url": f"{treatments}#treatment-{block.pk}",
        }
        paras = block.body_paragraphs()
        price_line = block.price_meta()
        desc_source = ""
        if price_line and len(paras) > 1:
            desc_source = paras[1]
        elif paras and not price_line:
            desc_source = paras[0]
        desc = " ".join(plain_cms_text(desc_source).split())
        if desc:
            item["description"] = desc[:240]
        offer = {"@type": "Offer", "itemOffered": item}
        found = _PRICE_RE.search(price_line or "")
        if found:
            offer["price"] = found.group(1)
            offer["priceCurrency"] = "SEK"
        offers.append(offer)
        if len(offers) >= _MAX_OFFERS:
            break
    if offers:
        return offers

    from booking.models import Service

    for service in Service.objects.filter(is_active=True).order_by("sort_order", "name"):
        item = {
            "@type": "Service",
            "name": service.name,
            "url": origin + reverse("booking") + "?service=" + service.slug,
        }
        if service.description:
            item["description"] = " ".join(service.description.split())[:240]
        offer = {"@type": "Offer", "itemOffered": item}
        if service.price_sek:
            offer["price"] = str(service.price_sek)
            offer["priceCurrency"] = "SEK"
        offers.append(offer)
        if len(offers) >= _MAX_OFFERS:
            break
    return offers


def _price_range(offers) -> str:
    prices = []
    for offer in offers:
        raw = offer.get("price")
        if raw and str(raw).isdigit():
            prices.append(int(raw))
    if not prices:
        return ""
    low, high = min(prices), max(prices)
    if low == high:
        return f"{low} SEK"
    return f"{low}-{high} SEK"


def local_business_json_ld(request, site) -> str:
    """Schema.org WebSite + BeautySalon for rich results.

    Hours come from Veckoschema. Prices come from Behandlingar-block.
    Adjust: phone, address, and public_site_url in SiteSettings admin.
    """
    origin = public_base_url(request, site).rstrip("/")
    offers = _treatment_offers(request, site)
    address = postal_address(getattr(site, "address", "") or "")
    image = ""
    if getattr(site, "logo", None):
        try:
            image = public_absolute_url(request, site, site.logo.url)
        except Exception:
            image = ""
    salon = {
        "@type": "BeautySalon",
        "@id": origin + "/#salon",
        "name": site.site_name,
        "description": site.default_meta_description or site.tagline,
        "url": origin + "/",
        "image": image or None,
        "logo": image or None,
        "email": site.email or None,
        "telephone": schema_telephone(site) or None,
        "currenciesAccepted": "SEK",
        "address": address,
        "areaServed": {
            "@type": "City",
            "name": address.get("addressLocality", DEFAULT_LOCALITY),
        },
        "openingHoursSpecification": _opening_hours() or None,
        "sameAs": [u for u in (site.facebook_url, site.linkedin_url) if u],
        "priceRange": _price_range(offers) or None,
        "hasOfferCatalog": {
            "@type": "OfferCatalog",
            "name": "Behandlingar och priser",
            "itemListElement": offers,
        }
        if offers
        else None,
        "potentialAction": {
            "@type": "ReserveAction",
            "target": {
                "@type": "EntryPoint",
                "urlTemplate": origin + reverse("booking"),
                "inLanguage": "sv-SE",
            },
            "name": "Boka tid",
        },
    }
    graph = {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "WebSite",
                "@id": origin + "/#website",
                "url": origin + "/",
                "name": site.site_name,
                "inLanguage": "sv-SE",
                "publisher": {"@id": origin + "/#salon"},
            },
            salon,
        ],
    }
    return dumps_ld(_clean(graph))


def page_structured_data(request, site):
    """WebPage JSON-LD and visible breadcrumb items for public pages.

    Returns (json_string, crumbs). Crumbs are empty on the home page.
    Links in the trail are relative so they stay on the host the visitor used.
    """
    match = getattr(request, "resolver_match", None)
    url_name = getattr(match, "url_name", None) if match else None
    if url_name not in PUBLIC_PAGES:
        return "", []
    origin = public_base_url(request, site).rstrip("/")
    page_url = canonical_url(request, site)
    label = PUBLIC_PAGES[url_name]
    is_home = url_name == "home"
    web_page = {
        "@type": "WebPage",
        "@id": page_url + "#webpage",
        "url": page_url,
        "name": site.site_name if is_home else label,
        "isPartOf": {"@id": origin + "/#website"},
        "about": {"@id": origin + "/#salon"},
        "inLanguage": "sv-SE",
    }
    if is_home and site.default_meta_description:
        web_page["description"] = site.default_meta_description
    graph = [web_page]
    crumbs = []
    if not is_home:
        web_page["breadcrumb"] = {"@id": page_url + "#breadcrumb"}
        graph.append(
            {
                "@type": "BreadcrumbList",
                "@id": page_url + "#breadcrumb",
                "itemListElement": [
                    {
                        "@type": "ListItem",
                        "position": 1,
                        "name": "Hem",
                        "item": origin + "/",
                    },
                    {
                        "@type": "ListItem",
                        "position": 2,
                        "name": label,
                        "item": page_url,
                    },
                ],
            }
        )
        crumbs = [
            {"name": "Hem", "url": reverse("home")},
            {"name": label, "url": request.path},
        ]
    payload = {"@context": "https://schema.org", "@graph": graph}
    return dumps_ld(_clean(payload)), crumbs
