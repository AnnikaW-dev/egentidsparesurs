# config/mail.py — resolve Django email settings from environment (local + Render)

"""Map EMAIL_* / SENDGRID_API_KEY env vars to Django mail settings.

Adjust: set SENDGRID_API_KEY on Render, or full SMTP vars for another provider.
"""

from __future__ import annotations

import os
from typing import TypedDict


class EmailConfig(TypedDict):
    backend: str
    host: str
    port: int
    user: str
    password: str
    use_tls: bool
    use_ssl: bool
    timeout: int
    default_from: str
    server_email: str


def env_bool(name: str, default: bool = False) -> bool:
    """Parse a boolean environment variable."""
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in ("1", "true", "yes", "on")


def resolve_email_config(*, debug: bool) -> EmailConfig:
    """Build email settings from env. SendGrid shorthand wins when SMTP host is unset."""
    default_from = os.environ.get("DEFAULT_FROM_EMAIL", "info@egentidspaservice.se").strip()
    server_email = os.environ.get("SERVER_EMAIL", default_from).strip()

    sendgrid_key = os.environ.get("SENDGRID_API_KEY", "").strip()
    host = os.environ.get("EMAIL_HOST", "").strip()
    user = os.environ.get("EMAIL_HOST_USER", "").strip()
    password = os.environ.get("EMAIL_HOST_PASSWORD", "").strip()

    if sendgrid_key and not host:
        host = "smtp.sendgrid.net"
        user = "apikey"
        password = sendgrid_key

    if debug:
        backend = os.environ.get(
            "EMAIL_BACKEND",
            "django.core.mail.backends.console.EmailBackend",
        )
    elif host:
        backend = os.environ.get(
            "EMAIL_BACKEND",
            "django.core.mail.backends.smtp.EmailBackend",
        )
    else:
        # Production without SMTP — keep console so the app boots; start.sh warns.
        backend = os.environ.get(
            "EMAIL_BACKEND",
            "django.core.mail.backends.console.EmailBackend",
        )

    port_raw = os.environ.get("EMAIL_PORT", "").strip()
    if port_raw:
        port = int(port_raw)
    elif host.endswith(":465") or env_bool("EMAIL_USE_SSL"):
        port = 465
    else:
        port = 587

    use_ssl = env_bool("EMAIL_USE_SSL", default=port == 465)
    use_tls = env_bool("EMAIL_USE_TLS", default=not use_ssl)

    return EmailConfig(
        backend=backend,
        host=host,
        port=port,
        user=user,
        password=password,
        use_tls=use_tls,
        use_ssl=use_ssl,
        timeout=int(os.environ.get("EMAIL_TIMEOUT", "30")),
        default_from=default_from,
        server_email=server_email,
    )


def smtp_is_configured(config: EmailConfig) -> bool:
    """True when production SMTP has host and credentials."""
    if "console" in config["backend"] or "locmem" in config["backend"]:
        return False
    if not config["host"]:
        return False
    # SendGrid and most relays require user + password.
    return bool(config["user"] and config["password"])


def apply_email_config(settings_module, *, debug: bool) -> None:
    """Write resolved email settings onto the Django settings module."""
    config = resolve_email_config(debug=debug)
    settings_module.EMAIL_BACKEND = config["backend"]
    settings_module.EMAIL_HOST = config["host"]
    settings_module.EMAIL_PORT = config["port"]
    settings_module.EMAIL_HOST_USER = config["user"]
    settings_module.EMAIL_HOST_PASSWORD = config["password"]
    settings_module.EMAIL_USE_TLS = config["use_tls"]
    settings_module.EMAIL_USE_SSL = config["use_ssl"]
    settings_module.EMAIL_TIMEOUT = config["timeout"]
    settings_module.DEFAULT_FROM_EMAIL = config["default_from"]
    settings_module.SERVER_EMAIL = config["server_email"]
    settings_module.EMAIL_IS_CONFIGURED = smtp_is_configured(config)
