# EGentid Spa & Resurs

Website for foot and hand care services (spa-pedikyr, värmande manikyr), inspired by the color scheme and content of [egentidsparesurs.wordpress.com](https://egentidsparesurs.wordpress.com/).

## Features

- Shared HTML templates (`templates/base.html`) for header, navigation, and footer across all pages
- Django admin for editing text, images, gallery, treatments, and site settings
- Public booking page with available time slots
- Staff dashboard (`/dashboard/`) to set weekly hours and generate slots for a week or month
- SEO (meta, sitemap, robots, JSON-LD) and EU accessibility baseline

## Local setup

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

- **Public site:** home, Salongen, Behandlingar, Året runt, Galleri, Boka, Kontakt
- **Content admin:** http://127.0.0.1:8000/admin/
- **Availability dashboard:** http://127.0.0.1:8000/dashboard/

## Deploy on Render

This repo includes `render.yaml`, `build.sh`, and `start.sh`.

1. Push this code to GitHub (`AnnikaW-dev/egentidsparesurs`).
2. In [Render](https://render.com): **New → Blueprint** → select the repo.
3. Apply the blueprint (creates a **web service** + **Postgres** + optional **disk** for media).
4. After the first deploy, open **`/admin/`** and log in with:
   - Username: value of `DJANGO_SUPERUSER_USERNAME` (default `admin`)
   - Password: from Render → your web service → **Environment** → `DJANGO_SUPERUSER_PASSWORD`  
   (created automatically on start — no Shell needed)
5. Change that password after first login. Set `SEED_ON_DEPLOY` to `false` after content is loaded.
6. In Django Admin → **Webbplatsinställningar → SEO**, set **public_site_url** to your `https://…` URL.
7. Optional: add a custom domain in Render, then add it to `ALLOWED_HOSTS` and `CSRF_TRUSTED_ORIGINS`.

**No Shell on free Render?** That is fine. Superuser and optional `seed_site` run from `start.sh` using env vars.
**Notes**

- Free Render disks may be limited; without a disk, uploaded media can disappear on redeploy. Prefer keeping the disk or later move media to S3/Cloudinary.
- Never commit real `SECRET_KEY` values; Render generates one via the blueprint.

## Updating content

| What | Where |
|------|--------|
| Logo, contact, footer, SEO | Admin → Webbplatsinställningar |
| Page titles & body text | Admin → Sidor |
| Gallery photos | Admin → Galleribilder |
| Treatment list & prices | Admin → Behandlingar |
| Weekly hours + generate slots | `/dashboard/tillganglighet/` |

## Design

Warm beige/brown palette from the WordPress site; Roboto / Roboto Condensed.
