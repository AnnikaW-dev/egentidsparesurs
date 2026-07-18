"""Public marketing pages driven by CMS SitePage content."""

from django.contrib import messages
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from cms.models import GalleryImage, SeasonTip, SitePage

from .forms import ContactForm


def _get_page(key):
    """Load a published CMS page by key, or None if missing."""
    return (
        SitePage.objects.filter(key=key, is_published=True)
        .prefetch_related("blocks")
        .first()
    )


def home(request):
    """Landing page with hero and featured content blocks."""
    page = _get_page(SitePage.PageKey.HOME)
    if not page:
        # Avoid hard 404 on fresh deploys before seed finishes / if seed failed.
        return render(request, "pages/setup_needed.html", status=200)
    blocks = page.blocks.filter(is_visible=True)
    return render(request, "pages/home.html", {"page": page, "blocks": blocks})


def salon(request):
    """About the salon."""
    page = _get_page(SitePage.PageKey.SALON)
    if not page:
        return render(request, "pages/setup_needed.html", status=200)
    return render(
        request,
        "pages/content_page.html",
        {"page": page, "blocks": page.blocks.filter(is_visible=True)},
    )


def treatments(request):
    """Treatments and oils overview."""
    page = _get_page(SitePage.PageKey.TREATMENTS)
    if not page:
        return render(request, "pages/setup_needed.html", status=200)
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
