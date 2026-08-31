"""Public marketing pages driven by CMS SitePage content."""

from django.contrib import messages
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from cms.models import GalleryImage, MonthHook, SeasonTip, SitePage

from .emails import send_contact_notification
from .forms import ContactForm


def _get_page(key):
    """Load a published CMS page by key, or None if missing."""
    return (
        SitePage.objects.filter(key=key, is_published=True)
        .select_related("hero_gallery_image")
        .prefetch_related("blocks", "hero_slides__gallery_image")
        .first()
    )


def home(request):
    """Landing page with hero, monthly recognition hook, and content blocks.

    Month hook: Admin → CMS → Känner du igen (current calendar month).
    """
    page = _get_page(SitePage.PageKey.HOME)
    if not page:
        return render(request, "pages/setup_needed.html", status=200)
    blocks = page.blocks.filter(is_visible=True)
    month_hook = MonthHook.objects.filter(
        month=timezone.localdate().month,
        is_visible=True,
    ).first()
    return render(
        request,
        "pages/home.html",
        {"page": page, "blocks": blocks, "month_hook": month_hook},
    )


def salon(request):
    """About the salon (nav label: Om)."""
    page = _get_page(SitePage.PageKey.SALON)
    if not page:
        return render(request, "pages/setup_needed.html", status=200)
    return render(
        request,
        "pages/content_page.html",
        {"page": page, "blocks": page.blocks.filter(is_visible=True)},
    )


def treatments(request):
    """Behandlingar & priser — CMS intro plus content blocks.

    Edit: Admin → Sidor → Behandlingar & priser → Innehållsblock.
    """
    page = _get_page(SitePage.PageKey.TREATMENTS)
    if not page:
        return render(request, "pages/setup_needed.html", status=200)
    return render(
        request,
        "pages/treatments.html",
        {"page": page, "blocks": page.blocks.filter(is_visible=True)},
    )


def warming(request):
    """Warming treatments (värmande behandlingar) CMS page."""
    page = _get_page(SitePage.PageKey.WARMING)
    if not page:
        return render(request, "pages/setup_needed.html", status=200)
    return render(
        request,
        "pages/content_page.html",
        {"page": page, "blocks": page.blocks.filter(is_visible=True)},
    )


def service_page(request):
    """Resource / administrative service offering (CMS key=service)."""
    page = _get_page(SitePage.PageKey.SERVICE)
    if not page:
        return render(request, "pages/setup_needed.html", status=200)
    return render(
        request,
        "pages/content_page.html",
        {"page": page, "blocks": page.blocks.filter(is_visible=True)},
    )


def seasons(request):
    """Året runt — intro plus tips for current month and the next two.

    Month tips: Admin → CMS → Säsongstips (one row per calendar month).
    """
    page = _get_page(SitePage.PageKey.SEASONS)
    season_tips = SeasonTip.tips_for_rolling_window()
    blocks = page.blocks.filter(is_visible=True) if page else []
    return render(
        request,
        "pages/seasons.html",
        {"page": page, "season_tips": season_tips, "blocks": blocks},
    )


def gallery(request):
    """Image gallery."""
    page = SitePage.objects.filter(key=SitePage.PageKey.GALLERY, is_published=True).first()
    images = GalleryImage.objects.filter(is_visible=True)
    return render(request, "pages/gallery.html", {"page": page, "images": images})


def accessibility(request):
    """EU accessibility statement (EAA / WCAG 2.1 AA)."""
    return render(request, "pages/accessibility.html")


def privacy(request):
    """Integritetspolicy — GDPR notice for contact and booking data."""
    return render(request, "pages/privacy.html")


@require_http_methods(["GET", "POST"])
def contact(request):
    """Show contact form and save submissions for staff in admin.

    Intro text: CMS SitePage key=contact (optional).
    Messages: Admin → Kontaktmeddelanden.
    """
    page = SitePage.objects.filter(key=SitePage.PageKey.CONTACT, is_published=True).first()
    form = ContactForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        message = form.save()
        send_contact_notification(message)
        messages.success(
            request,
            "Tack! Ditt meddelande är skickat. Vi återkommer så snart vi kan.",
        )
        return redirect("contact")

    return render(
        request,
        "pages/contact.html",
        {"page": page, "form": form},
    )
