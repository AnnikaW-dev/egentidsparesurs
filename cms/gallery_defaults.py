# cms/gallery_defaults.py — default Galleri images (static/img/gallery/)

"""Gallery seed list: filename under static/img/gallery/, title, caption.

Import source files: scripts/import_client_gallery.py
Live edits: Admin → CMS → Galleribilder
"""

# Adjust: (filename, title, caption) — sort_order follows list order in seed
GALLERY_IMAGES = [
    ("salon-lounge.jpg", "Väntrum", "Väntrum i salongen"),
    ("salon-interior.jpg", "Salongen", "Lugn och personlig miljö"),
    ("foot-bath.jpg", "Fotbad", "Fotbad i hemmasalongen"),
    ("foot-soak.jpg", "Fotbad hemma", "Avslappnande fotbad"),
    ("foot-massage.jpg", "Fotmassage", "Fotmassage med fokus på välmående"),
    ("foot-file.jpg", "Fotvård", "Fotvård med fil"),
    ("pedicure-foot-file.jpg", "Pedikyr", "Pedikyr och fotvård"),
    ("paraffin-foot-blue.jpg", "Paraffin fötter", "Värmande paraffinbad för fötter"),
    ("paraffin-foot-dip.jpg", "Paraffinbehandling fötter", "Paraffinbehandling för fötter"),
    ("paraffin-hand-blue.jpg", "Paraffin händer", "Värmande paraffinbad för händer"),
    ("paraffin-hand.jpg", "Paraffin hand", "Paraffinbehandling för händer"),
    ("paraffin-hand-wax.jpg", "Paraffin vax", "Paraffin vax på handen"),
    ("hand-massage.jpg", "Handmassage", "Handmassage"),
    ("hand-massage-oil.jpg", "Handmassage med olja", "Handmassage med olja"),
    ("manicure-drill.jpg", "Manikyr", "Manikyr och nagelvård"),
    ("spa-supplies.jpg", "Spaprodukter", "Spaprodukter och handdukar"),
    ("foot-anatomy.jpg", "Fotanatomi", "Kunskap bakom behandlingen"),
]

# UUID filenames in the client's Images folder → slug used in static/img/gallery/
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

CLIENT_VIDEO_NAME = "warming-paraffin.mp4"
CLIENT_VIDEO_SOURCE = "c6069fd9-8414-4a20-8a63-407bfac5cc10.mp4"
