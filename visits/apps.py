# visits/apps.py — app label shown as Besöksstatistik in admin

from django.apps import AppConfig


class VisitsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "visits"
    verbose_name = "Besöksstatistik"
