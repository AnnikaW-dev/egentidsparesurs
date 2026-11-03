"""Spam guards for the public contact form (timing, JS proof, floods, Turnstile).

Mirrors the awweb contact form. Turnstile runs only when both keys are set.
The JS proof must stay in sync with static/js/main.js (jsProofFor).
"""

from __future__ import annotations

import hashlib
import json
import logging
import secrets
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from django.conf import settings
from django.core.cache import cache
from django.core.signing import BadSignature, SignatureExpired, TimestampSigner

logger = logging.getLogger(__name__)

_GUARD_SALT = "egentid-form-guard-v1"
_JS_PREFIX = "eg1."
# Adjust: how often the same name or identical message may be sent.
_NAME_WINDOW = 6 * 60 * 60
_NAME_MAX = 4
_MSG_WINDOW = 6 * 60 * 60
_MSG_MAX = 3
_RATE_WINDOW = 60 * 60
_RATE_MAX = 5


def turnstile_enabled() -> bool:
    """True when both Cloudflare Turnstile keys are configured."""
    return bool(
        (getattr(settings, "TURNSTILE_SITE_KEY", "") or "").strip()
        and (getattr(settings, "TURNSTILE_SECRET_KEY", "") or "").strip()
    )


def turnstile_site_key() -> str:
    """Public site key for the widget, or empty when Turnstile is off."""
    if not turnstile_enabled():
        return ""
    return (settings.TURNSTILE_SITE_KEY or "").strip()


def issue_guard_token() -> str:
    """Signed token stamped with the time the form was rendered."""
    payload = f"{secrets.token_urlsafe(16)}.{int(time.time())}"
    return TimestampSigner(salt=_GUARD_SALT).sign(payload)


def js_proof_for(token: str) -> str:
    """Value the browser must place in form_js (mirrored in static/js/main.js)."""
    n = 0
    for i, ch in enumerate(token):
        n = (n + (ord(ch) * (i + 3))) % 1_000_000_007
    return f"{_JS_PREFIX}{n:08d}{len(token):04d}"


def validate_guard_token(token: str) -> str | None:
    """Return None if valid, else a short reason code for logs.

    Enforces max age, minimum fill time, and one-time use.
    """
    raw = (token or "").strip()
    if not raw:
        return "missing"
    min_seconds = int(getattr(settings, "FORM_GUARD_MIN_SECONDS", 3))
    max_age = int(getattr(settings, "FORM_GUARD_MAX_AGE", 60 * 60 * 12))
    signer = TimestampSigner(salt=_GUARD_SALT)
    try:
        payload = signer.unsign(raw, max_age=max_age)
    except SignatureExpired:
        return "expired"
    except BadSignature:
        return "bad"
    try:
        _nonce, issued_str = payload.rsplit(".", 1)
        issued = int(issued_str)
    except (TypeError, ValueError):
        return "bad"
    if time.time() - issued < min_seconds:
        return "too_fast"
    if cache.get(f"form-guard-used:{_fingerprint(raw)}"):
        return "reuse"
    return None


def mark_guard_used(token: str) -> None:
    """Remember a token so the same form cannot be posted twice."""
    raw = (token or "").strip()
    if not raw:
        return
    max_age = int(getattr(settings, "FORM_GUARD_MAX_AGE", 60 * 60 * 12))
    cache.set(f"form-guard-used:{_fingerprint(raw)}", 1, max_age)


def validate_js_proof(token: str, proof: str) -> bool:
    """True when form_js matches the checksum of form_guard."""
    expected = js_proof_for((token or "").strip())
    return secrets.compare_digest((proof or "").strip(), expected)


def _fingerprint(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:32]


def name_flood_limited(name: str, *, scope: str) -> bool:
    """True when the same display name was sent too often (rotating IPs)."""
    normalized = "".join((name or "").casefold().split())
    if len(normalized) < 2:
        return False
    return _bump_counter(
        f"form-name:{scope}:{_fingerprint(normalized)}",
        window=_NAME_WINDOW,
        limit=_NAME_MAX,
    )


def message_flood_limited(message: str, *, scope: str) -> bool:
    """True when the same message body was pasted too often."""
    normalized = " ".join((message or "").casefold().split())
    if len(normalized) < 20:
        return False
    return _bump_counter(
        f"form-msg:{scope}:{_fingerprint(normalized)}",
        window=_MSG_WINDOW,
        limit=_MSG_MAX,
    )


def submission_rate_limited(ip: str | None, *, scope: str) -> bool:
    """True when this IP already sent too many accepted messages this hour.

    The blocked attempt is not counted again. Empty IP is not limited.
    """
    if not ip:
        return False
    return _bump_counter(
        f"form-rate:{scope}:{_fingerprint(ip)}",
        window=_RATE_WINDOW,
        limit=_RATE_MAX,
    )


def _bump_counter(key: str, *, window: int, limit: int) -> bool:
    now = time.time()
    stamps = [t for t in cache.get(key, []) if now - t < window]
    if len(stamps) >= limit:
        cache.set(key, stamps, window)
        return True
    stamps.append(now)
    cache.set(key, stamps, window)
    return False


def verify_turnstile(response_token: str, remote_ip: str | None) -> bool:
    """Ask Cloudflare whether the Turnstile token is valid. False on any failure."""
    secret = (getattr(settings, "TURNSTILE_SECRET_KEY", "") or "").strip()
    token = (response_token or "").strip()
    if not secret or not token:
        return False
    payload: dict[str, Any] = {"secret": secret, "response": token}
    if remote_ip:
        payload["remoteip"] = remote_ip
    body = urllib.parse.urlencode(payload).encode("utf-8")
    req = urllib.request.Request(
        "https://challenges.cloudflare.com/turnstile/v0/siteverify",
        data=body,
        method="POST",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError):
        logger.exception("Turnstile verification request failed")
        return False
    return bool(data.get("success"))
