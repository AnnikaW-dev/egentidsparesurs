"""CMS helpers: context processors and lookups."""

from django.urls import reverse

from .models import SitePage, SiteSettings
from .seo import (
    canonical_url,
    local_business_json_ld,
    page_structured_data,
    public_absolute_url,
    public_base_url,
)


def site_settings(request):
    """Inject site branding and canonical SEO into every template."""
    site = SiteSettings.load()
    og_image_url = ""
    if site.og_image:
        og_image_url = public_absolute_url(request, site, site.og_image.url)
    elif site.logo:
        og_image_url = public_absolute_url(request, site, site.logo.url)
    json_ld_page, breadcrumbs = page_structured_data(request, site)

    return {
        "site": site,
        "canonical_url": canonical_url(request, site),
        "canonical_origin": public_base_url(request, site),
        "seo_description": site.default_meta_description,
        "og_image_url": og_image_url,
        "json_ld_business": local_business_json_ld(request, site),
        "json_ld_page": json_ld_page,
        "breadcrumbs": breadcrumbs,
        "home_url": canonical_url(request, site, reverse("home")),
        # Galleri is not in the main menu. Links exist only while the CMS page is published.
        "gallery_is_published": SitePage.objects.filter(
            key=SitePage.PageKey.GALLERY,
            is_published=True,
        ).exists(),
    }
