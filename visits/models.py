# visits/models.py — daily totals and anonymized visitor hashes for admin stats

from django.db import models


class SiteVisitor(models.Model):
    """Anonymized returning visitor. The hash cannot be reversed to an IP address."""

    visitor_hash = models.CharField(max_length=64, unique=True)
    first_seen = models.DateTimeField(auto_now_add=True)
    last_seen = models.DateTimeField(auto_now=True)
    last_seen_date = models.DateField()
    visit_count = models.PositiveIntegerField(default=1)

    class Meta:
        verbose_name = "besökare"
        verbose_name_plural = "besökare"

    def __str__(self) -> str:
        return self.visitor_hash[:12]


class SiteTrafficDay(models.Model):
    """One row per day. Admin shows these under Besöksstatistik."""

    day = models.DateField("datum", unique=True)
    pageviews = models.PositiveIntegerField("sidvisningar", default=0)
    unique_visitors = models.PositiveIntegerField("unika besökare", default=0)

    class Meta:
        ordering = ["-day"]
        verbose_name = "besöksdag"
        verbose_name_plural = "besöksstatistik"

    def __str__(self) -> str:
        return str(self.day)
