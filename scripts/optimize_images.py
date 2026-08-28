"""Optimize site images: resize, recompress JPEG, emit WebP companions.

Run: python scripts/optimize_images.py
Adjust TARGETS below if display sizes change.
"""

from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]

# (relative path under project, max box edge in px, jpeg quality)
TARGETS = [
    ("static/img/logo.png", 256, 85),
    ("static/img/hero-feet.jpg", 1400, 78),
    ("static/img/gallery-1.jpg", 900, 78),
    ("static/img/hand-massage.jpg", 1000, 80),
]


def knock_out_near_white(img: Image.Image, threshold: int = 245) -> Image.Image:
    """Remove near-white background connected to image edges (keeps light logo colors)."""
    from collections import deque

    img = img.convert("RGBA")
    w, h = img.size
    pixels = img.load()
    visited = [[False] * w for _ in range(h)]

    def is_background(r: int, g: int, b: int) -> bool:
        return r >= threshold and g >= threshold and b >= threshold

    queue = deque()
    for x in range(w):
        for y in (0, h - 1):
            if is_background(*pixels[x, y][:3]):
                queue.append((x, y))
    for y in range(h):
        for x in (0, w - 1):
            if is_background(*pixels[x, y][:3]):
                queue.append((x, y))

    while queue:
        x, y = queue.popleft()
        if x < 0 or x >= w or y < 0 or y >= h or visited[x][y]:
            continue
        r, g, b, _a = pixels[x, y]
        if not is_background(r, g, b):
            continue
        visited[x][y] = True
        pixels[x, y] = (r, g, b, 0)
        queue.extend([(x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)])

    # Erode near-white anti-alias halo left on the logo edge
    for _ in range(3):
        to_clear = []
        for y in range(h):
            for x in range(w):
                r, g, b, a = pixels[x, y]
                if a == 0:
                    continue
                if r >= 230 and g >= 230 and b >= 230:
                    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                        nx, ny = x + dx, y + dy
                        if 0 <= nx < w and 0 <= ny < h and pixels[nx, ny][3] == 0:
                            to_clear.append((x, y))
                            break
        for x, y in to_clear:
            r, g, b, _a = pixels[x, y]
            pixels[x, y] = (r, g, b, 0)

    return img


def optimize(path: Path, max_edge: int, quality: int) -> None:
    """Resize to max_edge, save optimized image + WebP next to it."""
    if not path.exists():
        print("skip missing", path)
        return
    img = Image.open(path)
    if path.suffix.lower() == ".png":
        img = knock_out_near_white(img)
        img.thumbnail((max_edge, max_edge), Image.Resampling.LANCZOS)
        img.save(path, "PNG", optimize=True)
        webp = path.with_suffix(".webp")
        img.save(webp, "WEBP", quality=quality, method=6)
        print(
            f"OK {path.name}: {img.size} -> {path.stat().st_size // 1024}KB + "
            f"{webp.name} {webp.stat().st_size // 1024}KB"
        )
        return
    img = img.convert("RGB")
    img.thumbnail((max_edge, max_edge), Image.Resampling.LANCZOS)

    img.save(path, "JPEG", quality=quality, optimize=True, progressive=True)
    webp = path.with_suffix(".webp")
    img.save(webp, "WEBP", quality=quality, method=6)
    print(f"OK {path.name}: {img.size} -> {path.stat().st_size // 1024}KB + {webp.name} {webp.stat().st_size // 1024}KB")


def mirror_to_media() -> None:
    """Copy optimized static heroes into common media upload paths."""
    mapping = {
        "static/img/logo.png": ["media/brand/logo.png"],
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


def ensure_media_webp() -> None:
    """Create .webp next to any media JPEG that is missing a companion."""
    media = ROOT / "media"
    if not media.exists():
        return
    for jpg in list(media.rglob("*.jpg")) + list(media.rglob("*.jpeg")):
        webp = jpg.with_suffix(".webp")
        if webp.exists():
            continue
        img = Image.open(jpg).convert("RGB")
        img.save(webp, "WEBP", quality=80, method=6)
        print("webp", webp.relative_to(ROOT))


def main():
    for rel, max_edge, quality in TARGETS:
        optimize(ROOT / rel, max_edge, quality)
    mirror_to_media()
    ensure_media_webp()
    # Drop leftover huge Django upload variants (same content, different names).
    for pattern in ("media/pages/hero-feet_*.jpg", "media/pages/gallery-1_*.jpg", "media/pages/hand-massage_*.jpg", "media/blocks/hand-massage_*.jpg"):
        for p in ROOT.glob(pattern):
            p.unlink(missing_ok=True)
            p.with_suffix(".webp").unlink(missing_ok=True)
            print("removed", p.relative_to(ROOT))


if __name__ == "__main__":
    main()
