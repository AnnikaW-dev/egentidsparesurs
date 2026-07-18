"""Optimize site images: resize, recompress JPEG, emit WebP companions.

Run: python scripts/optimize_images.py
Adjust TARGETS below if display sizes change.
"""

from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]

# (relative path under project, max box edge in px, jpeg quality)
TARGETS = [
    ("static/img/logo.jpg", 256, 82),
    ("static/img/hero-feet.jpg", 1400, 78),
    ("static/img/gallery-1.jpg", 900, 78),
    ("static/img/hand-massage.jpg", 1000, 80),
]


def optimize(path: Path, max_edge: int, quality: int) -> None:
    """Resize to max_edge, save optimized JPEG + WebP next to it."""
    if not path.exists():
        print("skip missing", path)
        return
    img = Image.open(path)
    img = img.convert("RGB")
    img.thumbnail((max_edge, max_edge), Image.Resampling.LANCZOS)

    img.save(path, "JPEG", quality=quality, optimize=True, progressive=True)
    webp = path.with_suffix(".webp")
    img.save(webp, "WEBP", quality=quality, method=6)
    print(f"OK {path.name}: {img.size} -> {path.stat().st_size // 1024}KB + {webp.name} {webp.stat().st_size // 1024}KB")


def mirror_to_media() -> None:
    """Copy optimized static heroes into common media upload paths."""
    mapping = {
        "static/img/logo.jpg": ["media/brand/logo.jpg"],
        "static/img/hero-feet.jpg": [
            "media/pages/hero-feet.jpg",
            "media/gallery/hero-feet.jpg",
        ],
        "static/img/gallery-1.jpg": [
            "media/pages/gallery-1.jpg",
            "media/gallery/gallery-1.jpg",
        ],
        "static/img/hand-massage.jpg": [
            "media/pages/hand-massage.jpg",
            "media/blocks/hand-massage.jpg",
            "media/gallery/hand-massage.jpg",
        ],
    }
    for src_rel, dests in mapping.items():
        src = ROOT / src_rel
        webp_src = src.with_suffix(".webp")
        for dest_rel in dests:
            dest = ROOT / dest_rel
            if not dest.parent.exists():
                continue
            dest.write_bytes(src.read_bytes())
            if webp_src.exists():
                dest.with_suffix(".webp").write_bytes(webp_src.read_bytes())
            print("mirrored", dest_rel)


def main():
    for rel, max_edge, quality in TARGETS:
        optimize(ROOT / rel, max_edge, quality)
    mirror_to_media()
    # Drop leftover huge Django upload variants (same content, different names).
    for pattern in ("media/pages/hero-feet_*.jpg", "media/pages/gallery-1_*.jpg", "media/pages/hand-massage_*.jpg", "media/blocks/hand-massage_*.jpg"):
        for p in ROOT.glob(pattern):
            p.unlink(missing_ok=True)
            print("removed", p.relative_to(ROOT))


if __name__ == "__main__":
    main()
