# cms/snapshot.py — export local CMS to git, apply the same content on Render

"""Copy SiteSettings, pages, blocks, gallery, tips, and media into a snapshot folder.

Local admin edits live in SQLite + media/ (not deployed). Render gets this snapshot
on boot via apply_site_snapshot. Re-export after content changes, then push.

Skip: bookings, users, contact messages, and tiny test uploads.
Never copy local public_site_url onto production.
"""

from __future__ import annotations

import hashlib
import json
import re
import shutil
from pathlib import Path

from django.conf import settings
from django.utils.text import slugify

from cms.models import (
    ContentBlock,
    GalleryImage,
    MonthHook,
    PageHeroSlide,
    SeasonTip,
    SitePage,
    SiteSettings,
)

SNAPSHOT_DIR = Path(__file__).resolve().parent / "content_snapshot"
CONTENT_NAME = "content.json"
FILES_DIRNAME = "files"
# Adjust: ignore leftover 1×1 PNGs from tests
MIN_MEDIA_BYTES = 1000
# Django ImageField suffix before the extension, e.g. hand-massage_ZcDjaBu.jpg
_HASH_SUFFIX = re.compile(r"_[A-Za-z0-9]{7}(?=\.[^.]+$)")


def snapshot_content_path(root: Path | None = None) -> Path:
    """JSON file listing pages, gallery, and relative media paths."""
    return (root or SNAPSHOT_DIR) / CONTENT_NAME


def snapshot_files_dir(root: Path | None = None) -> Path:
    """Folder of image files referenced by the snapshot JSON."""
    return (root or SNAPSHOT_DIR) / FILES_DIRNAME


def static_img_dir() -> Path:
    """Committed originals under static/img — used when snapshot has no copy."""
    return Path(settings.BASE_DIR) / "static" / "img"


def export_snapshot(dest: Path | None = None, stdout=None) -> Path:
    """Write local CMS + referenced images into dest (default cms/content_snapshot).

    Returns the snapshot root path.
    """
    root = dest or SNAPSHOT_DIR
    files_dir = snapshot_files_dir(root)
    if files_dir.exists():
        shutil.rmtree(files_dir)
    files_dir.mkdir(parents=True, exist_ok=True)

    used_names: set[str] = set()
    hash_to_rel: dict[str, str] = {}

    def store_image(image_field, *, hint: str = "") -> str:
        """Copy a usable ImageField into snapshot/files. Empty string if skipped."""
        return _store_image_field(
            image_field,
            files_dir,
            used_names,
            hash_to_rel,
            hint=hint,
        )

    site = SiteSettings.load()
    data = {
        "settings": {
            "site_name": site.site_name,
            "tagline": site.tagline,
            "email": site.email,
            "phone": site.phone,
            "address": site.address,
            "footer_text": site.footer_text,
            "facebook_url": site.facebook_url,
            "linkedin_url": site.linkedin_url,
            "default_meta_description": site.default_meta_description,
            "logo": store_image(site.logo, hint="logo"),
            "og_image": store_image(site.og_image, hint="og"),
        },
        "gallery": [],
        "pages": [],
        "season_tips": [],
        "month_hooks": [],
    }

    seen_gallery_files: set[str] = set()
    for gi in GalleryImage.objects.all().order_by("sort_order", "id"):
        rel = store_image(gi.image, hint=gi.title or "gallery")
        if not rel or rel in seen_gallery_files:
            continue
        seen_gallery_files.add(rel)
        data["gallery"].append(
            {
                "file": rel,
                "title": gi.title,
                "caption": gi.caption,
                "sort_order": gi.sort_order,
                "is_visible": gi.is_visible,
            }
        )

    gallery_by_id = {
        gi.pk: store_image(gi.image, hint=gi.title or "gallery")
        for gi in GalleryImage.objects.all()
    }

    skip_keys = {SitePage.PageKey.PRICES}
    for page in SitePage.objects.all().order_by("key"):
        if page.key in skip_keys:
            continue
        hero_gallery = ""
        if page.hero_gallery_image_id:
            hero_gallery = gallery_by_id.get(page.hero_gallery_image_id) or ""
        page_data = {
            "key": page.key,
            "title": page.title,
            "subtitle": page.subtitle,
            "body": page.body,
            "cta_primary": page.cta_primary,
            "cta_secondary": page.cta_secondary,
            "meta_title": page.meta_title,
            "meta_description": page.meta_description,
            "is_published": page.is_published,
            "hero": store_image(page.hero_image, hint=page.key),
            "hero_gallery": hero_gallery,
            "blocks": [],
            "hero_slides": [],
        }
        for block in page.blocks.all().order_by("sort_order", "id"):
            gal = ""
            if block.gallery_image_id:
                gal = gallery_by_id.get(block.gallery_image_id) or ""
            page_data["blocks"].append(
                {
                    "title": block.title,
                    "body": block.body,
                    "sort_order": block.sort_order,
                    "is_visible": block.is_visible,
                    "image": store_image(block.image, hint=block.title),
                    "gallery": gal,
                }
            )
        for slide in page.hero_slides.all().order_by("sort_order", "id"):
            gal = ""
            if slide.gallery_image_id:
                gal = gallery_by_id.get(slide.gallery_image_id) or ""
            page_data["hero_slides"].append(
                {
                    "sort_order": slide.sort_order,
                    "image": store_image(slide.image, hint="hero-slide"),
                    "gallery": gal,
                }
            )
        data["pages"].append(page_data)

    for tip in SeasonTip.objects.all().order_by("month"):
        data["season_tips"].append(
            {
                "month": tip.month,
                "title": tip.title,
                "icon": tip.icon,
                "body": tip.body,
                "closing_icon": tip.closing_icon,
                "closing_label": tip.closing_label,
                "closing_body": tip.closing_body,
                "closing_cta": tip.closing_cta,
                "is_featured": tip.is_featured,
                "is_visible": tip.is_visible,
                "image": store_image(tip.image, hint=f"season-{tip.month}"),
            }
        )
    for hook in MonthHook.objects.all().order_by("month"):
        data["month_hooks"].append(
            {
                "month": hook.month,
                "icon": hook.icon,
                "quote": hook.quote,
                "body": hook.body,
                "cta": hook.cta,
                "is_visible": hook.is_visible,
            }
        )

    content_path = snapshot_content_path(root)
    content_path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    if stdout:
        stdout.write(f"Wrote snapshot {content_path}")
    return root


def apply_snapshot(src: Path | None = None, stdout=None) -> bool:
    """Load snapshot into the current database and MEDIA_ROOT.

    Returns False if no snapshot file exists.
    Does not change public_site_url (Render / custom domain stays in env or admin).
    """
    root = src or SNAPSHOT_DIR
    content_path = snapshot_content_path(root)
    if not content_path.is_file():
        if stdout:
            stdout.write("No content snapshot — skip apply.")
        return False

    data = json.loads(content_path.read_text(encoding="utf-8"))
    files_dir = snapshot_files_dir(root)

    def place(rel: str) -> str:
        """Ensure MEDIA_ROOT has this relative file. Returns rel or empty."""
        return _place_media(rel, files_dir)

    gallery_by_file: dict[str, GalleryImage] = {}
    for item in data.get("gallery") or []:
        rel = place(item.get("file") or "")
        if not rel:
            continue
        gi = _upsert_gallery(item, rel)
        gallery_by_file[rel] = gi
        gallery_by_file[Path(rel).name] = gi

    site = SiteSettings.load()
    st = data.get("settings") or {}
    for field in (
        "site_name",
        "tagline",
        "email",
        "phone",
        "address",
        "footer_text",
        "facebook_url",
        "linkedin_url",
        "default_meta_description",
    ):
        if field in st and st[field] is not None:
            setattr(site, field, st[field])
    logo_rel = place(st.get("logo") or "")
    if logo_rel:
        site.logo.name = logo_rel
    og_rel = place(st.get("og_image") or "")
    if og_rel:
        site.og_image.name = og_rel
    site.save()

    keep_keys = []
    for page_data in data.get("pages") or []:
        key = page_data["key"]
        keep_keys.append(key)
        page, _created = SitePage.objects.update_or_create(
            key=key,
            defaults={
                "title": page_data.get("title") or "",
                "subtitle": page_data.get("subtitle") or "",
                "body": page_data.get("body") or "",
                "cta_primary": page_data.get("cta_primary") or "",
                "cta_secondary": page_data.get("cta_secondary") or "",
                "meta_title": page_data.get("meta_title") or "",
                "meta_description": page_data.get("meta_description") or "",
                "is_published": bool(page_data.get("is_published", True)),
            },
        )
        hero_rel = place(page_data.get("hero") or "")
        if hero_rel:
            page.hero_image.name = hero_rel
        gal_rel = page_data.get("hero_gallery") or ""
        page.hero_gallery_image = _gallery_ref(gal_rel, gallery_by_file)
        page.save()

        seen_orders = []
        for block_data in page_data.get("blocks") or []:
            order = int(block_data.get("sort_order") or 0)
            seen_orders.append(order)
            block, _ = ContentBlock.objects.update_or_create(
                page=page,
                sort_order=order,
                defaults={
                    "title": block_data.get("title") or "",
                    "body": block_data.get("body") or "",
                    "is_visible": bool(block_data.get("is_visible", True)),
                },
            )
            img_rel = place(block_data.get("image") or "")
            if img_rel:
                block.image.name = img_rel
            else:
                block.image = None
            block.gallery_image = _gallery_ref(
                block_data.get("gallery") or "", gallery_by_file
            )
            block.save()
        page.blocks.exclude(sort_order__in=seen_orders).delete()

        page.hero_slides.all().delete()
        for slide_data in page_data.get("hero_slides") or []:
            slide = PageHeroSlide(
                page=page,
                sort_order=int(slide_data.get("sort_order") or 0),
            )
            img_rel = place(slide_data.get("image") or "")
            if img_rel:
                slide.image.name = img_rel
            slide.gallery_image = _gallery_ref(
                slide_data.get("gallery") or "", gallery_by_file
            )
            slide.save()

    for tip_data in data.get("season_tips") or []:
        month = int(tip_data["month"])
        tip, _ = SeasonTip.objects.update_or_create(
            month=month,
            defaults={
                "title": tip_data.get("title") or "",
                "icon": tip_data.get("icon") or "",
                "body": tip_data.get("body") or "",
                "closing_icon": tip_data.get("closing_icon") or "",
                "closing_label": tip_data.get("closing_label") or "",
                "closing_body": tip_data.get("closing_body") or "",
                "closing_cta": tip_data.get("closing_cta") or "",
                "is_featured": bool(tip_data.get("is_featured", False)),
                "is_visible": bool(tip_data.get("is_visible", True)),
            },
        )
        img_rel = place(tip_data.get("image") or "")
        if img_rel:
            tip.image.name = img_rel
            tip.save(update_fields=["image"])

    for hook_data in data.get("month_hooks") or []:
        MonthHook.objects.update_or_create(
            month=int(hook_data["month"]),
            defaults={
                "icon": hook_data.get("icon") or "",
                "quote": hook_data.get("quote") or "",
                "body": hook_data.get("body") or "",
                "cta": hook_data.get("cta") or "",
                "is_visible": bool(hook_data.get("is_visible", True)),
            },
        )

    if stdout:
        stdout.write(f"Applied content snapshot ({len(keep_keys)} pages).")
    return True


def _gallery_ref(rel: str, by_file: dict) -> GalleryImage | None:
    if not rel:
        return None
    return by_file.get(rel) or by_file.get(Path(rel).name)


def _upsert_gallery(item: dict, rel: str) -> GalleryImage:
    gi = GalleryImage.objects.filter(image=rel).first()
    if not gi:
        gi = GalleryImage.objects.filter(image__endswith="/" + Path(rel).name).first()
    if not gi:
        gi = GalleryImage(image=rel)
    gi.title = item.get("title") or ""
    gi.caption = item.get("caption") or ""
    gi.sort_order = int(item.get("sort_order") or 0)
    gi.is_visible = bool(item.get("is_visible", True))
    gi.image.name = rel
    gi.save()
    return gi


def _place_media(rel: str, files_dir: Path) -> str:
    """Copy rel from snapshot files or static/img into MEDIA_ROOT. Return stored rel."""
    rel = (rel or "").replace("\\", "/").lstrip("/")
    if not rel or ".." in rel:
        return ""
    dest = Path(settings.MEDIA_ROOT) / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    src = _resolve_source(rel, files_dir)
    if src is None:
        return rel if dest.is_file() else ""
    if src.resolve() != dest.resolve():
        shutil.copy2(src, dest)
    webp_src = src.with_suffix(".webp")
    if webp_src.is_file():
        shutil.copy2(webp_src, dest.with_suffix(".webp"))
    else:
        _write_webp(dest)
    return rel


def _resolve_source(rel: str, files_dir: Path) -> Path | None:
    """Find a file in the snapshot, then static/img."""
    name = Path(rel).name
    candidates = [
        files_dir / rel,
        files_dir / name,
        static_img_dir() / name,
        static_img_dir() / "gallery" / name,
        static_img_dir() / "brand" / name,
    ]
    for path in candidates:
        if path.is_file() and path.stat().st_size >= MIN_MEDIA_BYTES:
            return path
    return None


def _store_image_field(image_field, files_dir, used_names, hash_to_rel, hint="") -> str:
    if not image_field or not image_field.name:
        return ""
    try:
        src = Path(image_field.path)
    except Exception:
        return ""
    if not src.is_file() or src.stat().st_size < MIN_MEDIA_BYTES:
        return ""

    digest = hashlib.sha256(src.read_bytes()).hexdigest()
    if digest in hash_to_rel:
        return hash_to_rel[digest]

    rel = _unique_rel(src, hint, used_names)
    dest = files_dir / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest = _copy_maybe_optimize(src, dest)
    rel = dest.relative_to(files_dir).as_posix()
    used_names.add(rel)
    hash_to_rel[digest] = rel
    webp = src.with_suffix(".webp")
    if webp.is_file() and dest.suffix.lower() == src.suffix.lower():
        shutil.copy2(webp, dest.with_suffix(".webp"))
    elif dest.suffix.lower() in {".jpg", ".jpeg", ".png"}:
        _write_webp(dest)
    return rel


def _unique_rel(src: Path, hint: str, used_names: set[str]) -> str:
    """Stable path under snapshot/files (gallery/, pages/, blocks/, brand/)."""
    folder = _folder_for(src)
    name = _HASH_SUFFIX.sub("", src.name)
    if name.lower().startswith("chatgpt") or " " in name:
        stem = slugify(hint or src.stem) or "image"
        name = stem + src.suffix.lower()
    rel = f"{folder}/{name}"
    if rel not in used_names:
        return rel
    stem = Path(name).stem
    suffix = Path(name).suffix
    n = 2
    while True:
        candidate = f"{folder}/{stem}-{n}{suffix}"
        if candidate not in used_names:
            return candidate
        n += 1


def _folder_for(src: Path) -> str:
    parts = {p.lower() for p in src.parts}
    if "gallery" in parts:
        return "gallery"
    if "blocks" in parts:
        return "blocks"
    if "brand" in parts:
        return "brand"
    if "pages" in parts:
        return "pages"
    if "heroes" in parts:
        return "heroes"
    if "seasons" in parts:
        return "seasons"
    if "seo" in parts:
        return "seo"
    return "uploads"


def _copy_maybe_optimize(src: Path, dest: Path) -> Path:
    """Copy src to dest; convert huge PNGs to JPEG. Returns the dest path used."""
    if src.suffix.lower() == ".png" and src.stat().st_size > 200_000:
        try:
            from PIL import Image

            img = Image.open(src).convert("RGB")
            dest = dest.with_suffix(".jpg")
            dest.parent.mkdir(parents=True, exist_ok=True)
            img.save(dest, "JPEG", quality=82, optimize=True, progressive=True)
            img.save(dest.with_suffix(".webp"), "WEBP", quality=82, method=6)
            return dest
        except Exception:
            pass
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dest)
    return dest


def _write_webp(path: Path) -> None:
    if path.suffix.lower() not in {".jpg", ".jpeg", ".png"}:
        return
    try:
        from PIL import Image

        img = Image.open(path)
        if path.suffix.lower() == ".png":
            img = img.convert("RGBA")
        else:
            img = img.convert("RGB")
        img.save(path.with_suffix(".webp"), "WEBP", quality=80, method=6)
    except Exception:
        return
