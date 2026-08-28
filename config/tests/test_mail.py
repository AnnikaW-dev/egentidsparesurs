"""Tests for email configuration helpers."""

import os
from unittest.mock import patch

from django.test import SimpleTestCase

from config.mail import apply_email_config, resolve_email_config, smtp_is_configured


class EmailConfigTests(SimpleTestCase):
    def test_sendgrid_shorthand_sets_smtp(self):
        env = {
            "SENDGRID_API_KEY": "sg.test-key",
            "DEFAULT_FROM_EMAIL": "info@example.com",
        }
        with patch.dict(os.environ, env, clear=False):
            os.environ.pop("EMAIL_HOST", None)
            config = resolve_email_config(debug=False)

        self.assertEqual(config["host"], "smtp.sendgrid.net")
        self.assertEqual(config["user"], "apikey")
        self.assertEqual(config["password"], "sg.test-key")
        self.assertTrue(smtp_is_configured(config))

    def test_apply_email_config_sets_flag(self):
        import config.settings as settings_module

        apply_email_config(settings_module, debug=True)
        self.assertIn("console", settings_module.EMAIL_BACKEND)
        self.assertFalse(settings_module.EMAIL_IS_CONFIGURED)
