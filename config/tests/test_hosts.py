"""Tests for ALLOWED_HOSTS / CSRF origin helpers."""

from django.test import SimpleTestCase

from config.hosts import sibling_hosts, trust_host, trust_url


class HostTrustTests(SimpleTestCase):
    def test_sibling_hosts_adds_www_and_apex(self):
        self.assertEqual(
            sibling_hosts("egentidspaservice.se"),
            ["egentidspaservice.se", "www.egentidspaservice.se"],
        )
        self.assertEqual(
            sibling_hosts("www.egentidspaservice.se"),
            ["www.egentidspaservice.se", "egentidspaservice.se"],
        )

    def test_trust_host_fills_allowed_hosts_and_csrf(self):
        allowed: list[str] = [".onrender.com"]
        csrf: list[str] = []
        trust_host("egentidspaservice.se", allowed, csrf)
        self.assertIn("egentidspaservice.se", allowed)
        self.assertIn("www.egentidspaservice.se", allowed)
        self.assertIn("https://egentidspaservice.se", csrf)
        self.assertIn("https://www.egentidspaservice.se", csrf)

    def test_trust_url_accepts_bare_domain(self):
        allowed: list[str] = []
        csrf: list[str] = []
        trust_url("www.egentidspaservice.se", allowed, csrf)
        self.assertIn("egentidspaservice.se", allowed)
        self.assertIn("https://www.egentidspaservice.se", csrf)
