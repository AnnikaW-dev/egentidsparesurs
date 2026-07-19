"""CMS helpers: context processors and lookups."""

from django.urls import reverse

from booking.models import WeeklyAvailability

from .models import SiteSettings
from .seo import absolute_url, local_business_json_ld


def site_settings(request):
    """Inject site branding, footer week hours, and default SEO into every template."""
    site = SiteSettings.load()
    og_image_url = ""
    if site.og_image:
        og_image_url = absolute_url(request, site.og_image.url)
    elif site.logo:
        og_image_url = absolute_url(request, site.logo.url)

    return {
        "site": site,
        # Adjust: sourced from WeeklyAvailability (dashboard / admin veckoschema)
        "footer_week_hours": WeeklyAvailability.footer_week_rows(),
        "canonical_url": absolute_url(request),
        "seo_description": site.default_meta_description,
        "og_image_url": og_image_url,
        "json_ld_business": local_business_json_ld(request, site),
        "home_url": absolute_url(request, reverse("home")),
    }
