# scripts/import_client_gallery.py — copy EGentid client photos into static/img/gallery/

"""Import JPEGs from the client's Images folder, optimize, and emit WebP.

Run: python scripts/import_client_gallery.py
Adjust CLIENT_IMAGES_DIR if the OneDrive path changes.
"""

from pathlib import Path

from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parents[1]

# Adjust: client Images folder on import machine (OneDrive path)
CLIENT_IMAGES_DIR = Path(
    r"C:\Users\awamn\OneDrive\Dokument\AWWeb\Kunder\EGentidSpaService\Images"
)
GALLERY_DIR = ROOT / "static" / "img" / "gallery"
VIDEO_DIR = ROOT / "static" / "video"
MAX_EDGE = 1200
JPEG_QUALITY = 78

CLIENT_IMAGE_MAP = {
    "54af6fe0-02bd-4a17-a22c-81c531250a97.jpeg": "salon-lounge.jpg",
    "8a9b76e9-0459-40a8-b297-0073ea1d8887.jpeg": "salon-interior.jpg",
    "8b12cbcc-fbc2-4c3d-8114-5ee31b06c665.jpeg": "foot-bath.jpg",
    "12a1796b-8a1d-4f27-bc48-4ea4fb17dba3.jpeg": "foot-soak.jpg",
    "5b4510e6-16ac-44f6-b52d-73ad5038081f.jpeg": "foot-massage.jpg",
    "198c7704-5e21-4148-bc7b-df69f16efab1.jpeg": "foot-file.jpg",
    "da4115f5-c2ff-4ff6-b15f-a7cf6147b86b.jpeg": "pedicure-foot-file.jpg",
    "82705355-dd52-4609-8f80-c0650551bfd2.jpeg": "paraffin-foot-blue.jpg",
    "c88fac45-2832-41d0-8ecf-398b88480bf7.jpeg": "paraffin-foot-dip.jpg",
    "9a447ef4-4b15-483a-ad28-f907e34b1010.jpeg": "paraffin-hand-blue.jpg",
    "d46cc3f1-ac75-4896-97ae-4ecd94cf4ec7.jpeg": "paraffin-hand.jpg",
    "4ca93754-841a-4f68-9cef-276b47905281.jpeg": "paraffin-hand-wax.jpg",
    "7de8ca34-e673-41f7-9258-f29257958726.jpeg": "hand-massage.jpg",
    "2136d393-ce4d-4d6d-a3d4-75a12099a288.jpeg": "hand-massage-oil.jpg",
    "5fa682b5-6476-49d4-bfdd-4dff06bbc4a2.jpeg": "manicure-drill.jpg",
    "00d2db79-5b61-490f-8458-e7e79549f390.jpeg": "spa-supplies.jpg",
    "39fd3959-f6cf-4a2a-8b20-80bb413501bd.jpeg": "foot-anatomy.jpg",
}
CLIENT_VIDEO_SOURCE = "c6069fd9-8414-4a20-8a63-407bfac5cc10.mp4"
CLIENT_VIDEO_NAME = "warming-paraffin.mp4"


def optimize_jpeg(path: Path) -> None:
    """Resize, auto-orient, save JPEG + WebP."""
    img = ImageOps.exif_transpose(Image.open(path))
    img = img.convert("RGB")
    img.thumbnail((MAX_EDGE, MAX_EDGE), Image.Resampling.LANCZOS)
    img.save(path, "JPEG", quality=JPEG_QUALITY, optimize=True, progressive=True)
    img.save(path.with_suffix(".webp"), "WEBP", quality=JPEG_QUALITY, method=6)
    print(
        f"OK {path.name}: {img.size} -> "
        f"{path.stat().st_size // 1024}KB + {path.with_suffix('.webp').name}"
    )


def import_gallery() -> int:
    """Copy mapped client JPEGs into static/img/gallery/. Returns count imported."""
    GALLERY_DIR.mkdir(parents=True, exist_ok=True)
    count = 0
    for src_name, dest_name in CLIENT_IMAGE_MAP.items():
        src = CLIENT_IMAGES_DIR / src_name
        if not src.exists():
            print("skip missing", src_name)
            continue
        dest = GALLERY_DIR / dest_name
        dest.write_bytes(src.read_bytes())
        optimize_jpeg(dest)
        count += 1
    return count


def import_video() -> bool:
    """Copy client MP4 into static/video/ (stored only — not shown on any page by default)."""
    src = CLIENT_IMAGES_DIR / CLIENT_VIDEO_SOURCE
    if not src.exists():
        print("skip missing video", CLIENT_VIDEO_SOURCE)
        return False
    VIDEO_DIR.mkdir(parents=True, exist_ok=True)
    dest = VIDEO_DIR / CLIENT_VIDEO_NAME
    dest.write_bytes(src.read_bytes())
    print(f"OK video {dest.name}: {dest.stat().st_size // 1024}KB")
    return True


def main() -> None:
    if not CLIENT_IMAGES_DIR.is_dir():
        raise SystemExit(f"Client folder not found: {CLIENT_IMAGES_DIR}")
    n = import_gallery()
    import_video()
    print(f"Imported {n} gallery images into {GALLERY_DIR.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
