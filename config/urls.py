"""URL routes for EGentid Spa & Resurs."""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.sitemaps.views import sitemap
from django.urls import path
from django.views.generic import TemplateView

from booking import views as booking_views
from pages import views as page_views
from pages.sitemaps import StaticViewSitemap

sitemaps = {
    "static": StaticViewSitemap,
}

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", page_views.home, name="home"),
    path("salongen/", page_views.salon, name="salon"),
    path("behandlingar/", page_views.treatments, name="treatments"),
    path("aret-runt/", page_views.seasons, name="seasons"),
    path("galleri/", page_views.gallery, name="gallery"),
    path("kontakt/", page_views.contact, name="contact"),
    path("tillganglighet/", page_views.accessibility, name="accessibility"),
    path("boka/", booking_views.booking_page, name="booking"),
    path("boka/bekraftelse/<int:pk>/", booking_views.booking_success, name="booking_success"),
    path("dashboard/", booking_views.dashboard_home, name="dashboard"),
    path("dashboard/tillganglighet/", booking_views.dashboard_availability, name="dashboard_availability"),
    path(
        "sitemap.xml",
        sitemap,
        {"sitemaps": sitemaps},
        name="django.contrib.sitemaps.views.sitemap",
    ),
    path(
        "robots.txt",
        TemplateView.as_view(template_name="robots.txt", content_type="text/plain"),
        name="robots_txt",
    ),
]

admin.site.site_header = "EGentid Spa & Resurs – Admin"
admin.site.site_title = "EGentid Admin"
admin.site.index_title = "Innehåll & bokningar"

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATICFILES_DIRS[0])
