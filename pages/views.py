"""Public marketing pages driven by CMS SitePage content."""

from django.contrib import messages
from django.http import Http404
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from booking.models import Service
from cms.models import GalleryImage, SeasonTip, SitePage

from .forms import ContactForm


def _get_page(key):
    """Load a published CMS page by key, or 404."""
    page = SitePage.objects.filter(key=key, is_published=True).prefetch_related("blocks").first()
    if not page:
        raise Http404("Sidan finns inte ännu.")
    return page


def home(request):
    """Landing page with hero, monthly tip, and featured content blocks.

    Monthly tip: Admin → Säsongstips → row for the current month.
    """
    page = _get_page(SitePage.PageKey.HOME)
    blocks = page.blocks.filter(is_visible=True)
    month_tip = SeasonTip.objects.filter(
        month=timezone.localdate().month,
        is_visible=True,
    ).first()
    return render(
        request,
        "pages/home.html",
        {"page": page, "blocks": blocks, "month_tip": month_tip},
    )


def salon(request):
    """About the salon (nav label: Om)."""
    page = _get_page(SitePage.PageKey.SALON)
    return render(
        request,
        "pages/content_page.html",
        {"page": page, "blocks": page.blocks.filter(is_visible=True)},
    )


def treatments(request):
    """Treatments and oils overview."""
    page = _get_page(SitePage.PageKey.TREATMENTS)
    return render(
        request,
        "pages/content_page.html",
        {"page": page, "blocks": page.blocks.filter(is_visible=True)},
    )


def warming(request):
    """Warming treatments (värmande behandlingar) CMS page."""
    page = _get_page(SitePage.PageKey.WARMING)
    return render(
        request,
        "pages/content_page.html",
        {"page": page, "blocks": page.blocks.filter(is_visible=True)},
    )


def prices(request):
    """Price list — CMS intro plus content blocks on SitePage key=prices.

    Edit treatments: Admin → Sidor → Prislista → Innehållsblock.
    """
    page = SitePage.objects.filter(key=SitePage.PageKey.PRICES, is_published=True).prefetch_related("blocks").first()
    if not page:
        raise Http404("Sidan finns inte ännu.")
    return render(
        request,
        "pages/prices.html",
        {
            "page": page,
            "blocks": page.blocks.filter(is_visible=True),
        },
    )


def service_page(request):
    """Resource / administrative service offering (CMS key=service)."""
    page = _get_page(SitePage.PageKey.SERVICE)
    return render(
        request,
        "pages/content_page.html",
        {"page": page, "blocks": page.blocks.filter(is_visible=True)},
    )


def seasons(request):
    """Year-round seasonal tips."""
    page = _get_page(SitePage.PageKey.SEASONS)
    tips = SeasonTip.objects.filter(is_visible=True)
    return render(request, "pages/seasons.html", {"page": page, "tips": tips})


def gallery(request):
    """Image gallery."""
    page = SitePage.objects.filter(key=SitePage.PageKey.GALLERY, is_published=True).first()
    images = GalleryImage.objects.filter(is_visible=True)
    return render(request, "pages/gallery.html", {"page": page, "images": images})


def accessibility(request):
    """EU accessibility statement (EAA / WCAG 2.1 AA)."""
    return render(request, "pages/accessibility.html")


@require_http_methods(["GET", "POST"])
def contact(request):
    """Show contact form and save submissions for staff in admin.

    Intro text: CMS SitePage key=contact (optional).
    Messages: Admin → Kontaktmeddelanden.
    """
    page = SitePage.objects.filter(key=SitePage.PageKey.CONTACT, is_published=True).first()
    form = ContactForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        form.save()
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
