"""Shared body text parsing for CMS models (## headings, ✔ lists, paragraphs)."""


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
        if line.startswith(("✔", "✓")):
            checklist.append(line.lstrip("✔✓").strip())
            continue
        flush_list()
        if line.startswith("## "):
            sections.append({"type": "heading", "text": line[3:].strip()})
        else:
            sections.append({"type": "para", "text": line})
    flush_list()
    return sections
