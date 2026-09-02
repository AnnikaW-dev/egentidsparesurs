# config/hosts.py — ALLOWED_HOSTS and CSRF origins for Render + custom domains

"""Trust a hostname for Django Host and CSRF checks.

Django returns 400 Bad Request when the request Host is not in ALLOWED_HOSTS.
Adjust: add live domains in PRODUCTION_HOSTS or PUBLIC_SITE_URL.
"""

from __future__ import annotations

from urllib.parse import urlparse

# Live site — both names must be allowed (Render redirects www ↔ apex).
# Adjust: change these if the public domain changes.
PRODUCTION_HOSTS = ("egentidspaservice.se", "www.egentidspaservice.se")

_NO_WWW_SIBLING = frozenset({"localhost", "127.0.0.1", "testserver", "0.0.0.0"})


def sibling_hosts(host: str) -> list[str]:
    """Return host plus the www/apex counterpart (skip IPs and local names)."""
    host = (host or "").strip().lower().rstrip(".")
    if not host or host.startswith(".") or host in _NO_WWW_SIBLING:
        return [host] if host else []
    if host.replace(".", "").isdigit():
        return [host]
    if host.startswith("www.") and host.count(".") >= 2:
        return [host, host[4:]]
    return [host, f"www.{host}"]


def trust_host(host: str, allowed_hosts: list[str], csrf_origins: list[str], *, scheme: str = "https") -> None:
    """Append host (and www/apex sibling) to ALLOWED_HOSTS and CSRF_TRUSTED_ORIGINS."""
    for name in sibling_hosts(host):
        if name and name not in allowed_hosts:
            allowed_hosts.append(name)
        if not name or name.startswith(".") or name in _NO_WWW_SIBLING:
            continue
        origin = f"{scheme}://{name}"
        if origin not in csrf_origins:
            csrf_origins.append(origin)


def trust_url(url: str, allowed_hosts: list[str], csrf_origins: list[str]) -> None:
    """Trust hostname from a full URL or a bare domain."""
    raw = (url or "").strip()
    if not raw:
        return
    if "://" not in raw:
        raw = "https://" + raw
    parsed = urlparse(raw)
    host = parsed.hostname
    if not host:
        return
    scheme = parsed.scheme or "https"
    if host in _NO_WWW_SIBLING or host.replace(".", "").isdigit():
        scheme = parsed.scheme or "http"
    trust_host(host, allowed_hosts, csrf_origins, scheme=scheme)
