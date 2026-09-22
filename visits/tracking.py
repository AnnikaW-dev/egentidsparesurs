# visits/tracking.py — count public GET pages; skip admin, staff, bots, and assets

import hashlib
import logging
from datetime import timedelta

from django.conf import settings
from django.db import IntegrityError, transaction
from django.db.models import F, Sum
from django.http import HttpRequest
from django.utils import timezone

from .models import SiteTrafficDay, SiteVisitor

logger = logging.getLogger(__name__)

_SKIP_PREFIXES = (
    "/admin/",
    "/dashboard/",
    "/static/",
    "/media/",
    "/healthz",
)
_SKIP_EXACT = {
    "/robots.txt",
    "/favicon.ico",
    "/sitemap.xml",
}
_SKIP_SUFFIXES = (
    ".css",
    ".js",
    ".map",
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".svg",
    ".ico",
    ".webp",
    ".woff",
    ".woff2",
    ".json",
    ".txt",
    ".xml",
    ".mp4",
    ".vtt",
)
_BOT_MARKERS = (
    "bot",
    "crawler",
    "spider",
    "crawling",
    "slurp",
    "bingpreview",
    "facebookexternalhit",
    "linkedinbot",
    "embedly",
    "whatsapp",
    "telegram",
    "skypeuripreview",
    "semrush",
    "ahrefs",
    "petalbot",
    "bytespider",
    "gptbot",
    "claudebot",
    "ccbot",
    "preview",
    "curl/",
    "wget/",
    "python-requests",
    "http-client",
)


def client_ip(request: HttpRequest) -> str | None:
    """First address in X-Forwarded-For, otherwise REMOTE_ADDR. Used only to build a hash."""
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded:
        return forwarded.split(",")[0].strip()
    ip = request.META.get("REMOTE_ADDR")
    return ip if ip else None


def should_skip_path(path: str) -> bool:
    """True for admin, dashboard, assets, and non-page files."""
    lowered = (path or "/").lower()
    if lowered in _SKIP_EXACT:
        return True
    if lowered.startswith(_SKIP_PREFIXES):
        return True
    return any(lowered.endswith(suffix) for suffix in _SKIP_SUFFIXES)


def is_bot(request) -> bool:
    """Empty or known crawler user agents are not counted."""
    ua = (request.META.get("HTTP_USER_AGENT") or "").lower()
    if not ua:
        return True
    return any(marker in ua for marker in _BOT_MARKERS)


def visitor_hash(request) -> str:
    """One-way hash of IP + user agent. The raw IP is not stored."""
    ip = client_ip(request) or "unknown"
    ua = (request.META.get("HTTP_USER_AGENT") or "")[:120]
    material = f"{ip}|{ua}|visit|{settings.SECRET_KEY}"
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def record_visit(request, response) -> None:
    """Increment today's pageviews. A visitor counts once per local day.

    Staff, bots, prefetches, and non-200 responses are ignored.
    Failures are logged and never change the page the visitor sees.
    """
    if request.method != "GET":
        return
    if getattr(response, "status_code", 0) != 200:
        return
    if should_skip_path(request.path):
        return
    if request.headers.get("Sec-Purpose") == "prefetch":
        return
    if request.headers.get("Purpose") == "prefetch":
        return
    user = getattr(request, "user", None)
    if user is not None and getattr(user, "is_staff", False):
        return
    if is_bot(request):
        return

    today = timezone.localdate()
    digest = visitor_hash(request)
    try:
        with transaction.atomic():
            visitor, created = SiteVisitor.objects.get_or_create(
                visitor_hash=digest,
                defaults={"last_seen_date": today, "visit_count": 1},
            )
            first_today = created or visitor.last_seen_date != today
            if not created:
                SiteVisitor.objects.filter(pk=visitor.pk).update(
                    visit_count=F("visit_count") + 1,
                    last_seen=timezone.now(),
                    last_seen_date=today,
                )
            day, day_created = SiteTrafficDay.objects.get_or_create(
                day=today,
                defaults={
                    "pageviews": 1,
                    "unique_visitors": 1,
                },
            )
            if not day_created:
                updates = {"pageviews": F("pageviews") + 1}
                if first_today:
                    updates["unique_visitors"] = F("unique_visitors") + 1
                SiteTrafficDay.objects.filter(pk=day.pk).update(**updates)
    except IntegrityError:
        logger.warning("Visit tracking raced; skipping this hit.")
    except Exception:
        logger.exception("Visit tracking failed")


def traffic_summary() -> dict:
    """Totals for the admin overview: today, 7 days, 30 days, and all time."""
    today = timezone.localdate()
    week_start = today - timedelta(days=6)
    month_start = today - timedelta(days=29)
    today_row = SiteTrafficDay.objects.filter(day=today).first()
    week = SiteTrafficDay.objects.filter(day__gte=week_start).aggregate(
        views=Sum("pageviews"),
        uniques=Sum("unique_visitors"),
    )
    month = SiteTrafficDay.objects.filter(day__gte=month_start).aggregate(
        views=Sum("pageviews"),
        uniques=Sum("unique_visitors"),
    )
    total = SiteTrafficDay.objects.aggregate(views=Sum("pageviews"))
    return {
        "today_views": today_row.pageviews if today_row else 0,
        "today_unique": today_row.unique_visitors if today_row else 0,
        "week_views": week["views"] or 0,
        "week_unique": SiteVisitor.objects.filter(last_seen_date__gte=week_start).count(),
        "month_views": month["views"] or 0,
        "month_unique": SiteVisitor.objects.filter(last_seen_date__gte=month_start).count(),
        "total_views": total["views"] or 0,
        "total_unique": SiteVisitor.objects.count(),
    }
