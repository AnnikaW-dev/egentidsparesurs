# EGentid Spa & Resurs

Website for foot and hand care services (spa-pedikyr, värmande manikyr), inspired by the color scheme and content of [egentidsparesurs.wordpress.com](https://egentidsparesurs.wordpress.com/).

## Features

- Shared HTML templates (`templates/base.html`) for header, navigation, and footer across all pages
- Django admin for editing text, images, gallery, treatments, and site settings
- Public booking page with available time slots
- Staff dashboard (`/dashboard/`) to set weekly hours and generate slots for a week or month

## Setup

```bash
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_site
python manage.py createsuperuser
python manage.py runserver
```

Open http://127.0.0.1:8000/

- **Public site:** home, Salongen, Behandlingar, Året runt, Galleri, Boka
- **Content admin:** http://127.0.0.1:8000/admin/
- **Availability dashboard:** http://127.0.0.1:8000/dashboard/

## Updating content

| What | Where |
|------|--------|
| Logo, contact, footer | Admin → Webbplatsinställningar |
| Page titles & body text | Admin → Sidor |
| Gallery photos | Admin → Galleribilder |
| Treatment list & prices | Admin → Behandlingar |
| Weekly hours + generate slots | `/dashboard/tillganglighet/` |

## Design

Palette from the WordPress site: background `#C3B09C`, text `#7C654F`, Roboto / Roboto Condensed.
