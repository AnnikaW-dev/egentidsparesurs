"""Shared body text parsing for CMS models (## headings, ✔/• lists, **bold**)."""

import re
from html import escape

from django.utils.safestring import mark_safe

# Shown in admin help — how editors mark bold text
BOLD_MARKUP_HINT = "Fet stil: skriv **text** (dubbla asterisker runt ordet)."

_BOLD_RE = re.compile(r"\*\*(.+?)\*\*")


def normalize_newlines(text: str) -> str:
    """Turn Windows CRLF from admin into LF so blank lines still split paragraphs."""
    return (text or "").replace("\r\n", "\n").replace("\r", "\n")


def format_inline_markup(text: str, *, newlines: bool = False):
    """Escape HTML, then turn **bold** into <strong>. Safe for templates.

    Adjust: only **…** is supported; raw HTML from admin is not rendered.
    Set newlines=True to turn line breaks into <br> (e.g. footer address).
    """
    if text is None:
        return ""
    raw = str(text)
    if not raw:
        return ""
    escaped = escape(raw)
    html = _BOLD_RE.sub(r"<strong>\1</strong>", escaped)
    if newlines:
        html = html.replace("\r\n", "\n").replace("\r", "\n").replace("\n", "<br>")
    return mark_safe(html)


def parse_body_sections(body: str):
    """Parse body into heading / paragraph / checklist blocks for templates."""
    sections = []
    checklist = []

    def flush_list():
        nonlocal checklist
        if checklist:
            sections.append({"type": "list", "items": checklist})
            checklist = []

    for raw in body.splitlines():
        line = raw.strip()
        if not line:
            flush_list()
            continue
        if line.startswith(("✔", "✓", "•")) or line.startswith("- "):
            item = line
            for prefix in ("✔", "✓", "•", "- "):
                if item.startswith(prefix):
                    item = item[len(prefix) :].strip()
                    break
            checklist.append(item)
            continue
        flush_list()
        if line.startswith("## "):
            sections.append({"type": "heading", "text": line[3:].strip()})
        else:
            sections.append({"type": "para", "text": line})
    flush_list()
    return sections
