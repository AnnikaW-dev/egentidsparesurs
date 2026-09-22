# visits/tests.py — public pages increment admin stats; staff, bots, and admin do not

from django.contrib.auth.models import User
from django.test import Client, TestCase


class VisitTrackingTests(TestCase):
    browser = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )

    def _get(self, path, **kwargs):
        kwargs.setdefault("HTTP_USER_AGENT", self.browser)
        return self.client.get(path, **kwargs)

    def test_public_page_counts_unique_visitors_and_pageviews(self):
        from visits.models import SiteTrafficDay, SiteVisitor

        self._get("/")
        self._get("/")
        self.assertEqual(SiteVisitor.objects.count(), 1)
        day = SiteTrafficDay.objects.get()
        self.assertEqual(day.pageviews, 2)
        self.assertEqual(day.unique_visitors, 1)

    def test_different_ips_count_as_different_visitors(self):
        from visits.models import SiteTrafficDay, SiteVisitor

        self._get("/", REMOTE_ADDR="1.1.1.1")
        self._get("/", REMOTE_ADDR="8.8.8.8")
        self.assertEqual(SiteVisitor.objects.count(), 2)
        self.assertEqual(SiteTrafficDay.objects.get().unique_visitors, 2)
        self.assertEqual(SiteTrafficDay.objects.get().pageviews, 2)

    def test_admin_assets_and_bots_are_not_counted(self):
        from visits.models import SiteTrafficDay

        self._get("/robots.txt")
        self._get("/admin/")
        self._get("/dashboard/")
        self.client.get("/", HTTP_USER_AGENT="Mozilla/5.0 Googlebot/2.1")
        self.assertEqual(SiteTrafficDay.objects.count(), 0)

    def test_staff_is_not_counted(self):
        from visits.models import SiteTrafficDay

        user = User.objects.create_user("annika", password="test-password-12", is_staff=True)
        self.client.force_login(user)
        self._get("/")
        self.assertEqual(SiteTrafficDay.objects.count(), 0)

    def test_admin_overview_shows_totals(self):
        from visits.models import SiteTrafficDay

        self._get("/")
        User.objects.create_superuser("admin", "a@example.com", "test-password-12")
        self.client.login(username="admin", password="test-password-12")
        response = self.client.get("/admin/visits/sitetrafficday/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Besöksstatistik")
        self.assertContains(response, "Översikt")
        self.assertContains(response, "Unika besökare")
        self.assertContains(response, str(SiteTrafficDay.objects.get().pageviews))

    def test_admin_index_links_to_visit_stats(self):
        User.objects.create_superuser("admin", "a@example.com", "test-password-12")
        self.client.login(username="admin", password="test-password-12")
        response = self.client.get("/admin/")
        self.assertContains(response, "Besöksstatistik")
        self.assertContains(response, "/admin/visits/sitetrafficday/")


class PrivacyMentionsVisitStatsTests(TestCase):
    """The policy names anonymous visit counts without changing the cookie wording."""

    def test_privacy_page_mentions_anonymous_stats(self):
        response = Client().get("/integritet/")
        self.assertContains(response, "Besöksstatistik")
        self.assertContains(response, "statistik, reklam eller spårning")
