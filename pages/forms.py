"""Forms for public pages (contact) — labels, autocomplete, a11y attrs."""

import logging

from django import forms
from django.core.validators import EmailValidator, RegexValidator

from visits.tracking import client_ip

from .antispam import (
    issue_guard_token,
    mark_guard_used,
    message_flood_limited,
    name_flood_limited,
    turnstile_enabled,
    validate_guard_token,
    validate_js_proof,
    verify_turnstile,
)
from .models import ContactMessage

logger = logging.getLogger(__name__)

# Adjust: shared Swedish copy for invalid e-post (contact + booking)
EMAIL_INVALID_MSG = "Ange en giltig e-postadress, t.ex. namn@exempel.se."
EMAIL_REQUIRED_MSG = "Ange en e-postadress."
PHONE_DIGITS_MSG = "Telefonnummer får bara innehålla siffror."


class TelInput(forms.TextInput):
    """Telephone field — single type=tel (avoids type=text + type=tel duplicate)."""

    input_type = "tel"


def configure_email_field(field):
    """Restrict to valid e-post and show Swedish messages when rules fail."""
    field.required = True
    field.error_messages = {
        **field.error_messages,
        "required": EMAIL_REQUIRED_MSG,
        "invalid": EMAIL_INVALID_MSG,
    }
    field.validators = [
        EmailValidator(message=EMAIL_INVALID_MSG),
    ]
    field.widget.attrs.update(
        {
            "inputmode": "email",
            "autocomplete": "email",
            "spellcheck": "false",
            "title": EMAIL_INVALID_MSG,
            "data-validate-email": "true",
        }
    )


def configure_phone_field(field, *, required=False):
    """Allow digits only in Telefon; show Swedish message if other characters appear."""
    field.required = required
    field.error_messages = {
        **field.error_messages,
        "invalid": PHONE_DIGITS_MSG,
    }
    field.validators = [
        RegexValidator(regex=r"^\d*$", message=PHONE_DIGITS_MSG),
    ]
    field.widget.attrs.update(
        {
            "inputmode": "numeric",
            "autocomplete": "tel",
            "title": PHONE_DIGITS_MSG,
            "data-digits-only": "true",
        }
    )


def clean_digits_only(value, *, required=False):
    """Strip spaces; reject anything that is not digits (empty OK if optional)."""
    phone = (value or "").strip().replace(" ", "")
    if not phone:
        if required:
            raise forms.ValidationError("Ange ett telefonnummer.")
        return ""
    if not phone.isdigit():
        raise forms.ValidationError(PHONE_DIGITS_MSG)
    return phone


class AntiSpamFormMixin:
    """Timing token, JS proof, content floods, optional Cloudflare Turnstile.

    Pass request= so Turnstile can include the client IP. Hidden fields are
    form_guard, form_js, and (when keys exist) cf-turnstile-response.
    """

    antispam_scope = "form"
    antispam_reject_message = "Meddelandet kunde inte skickas."

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop("request", None)
        super().__init__(*args, **kwargs)
        self.fields["form_guard"] = forms.CharField(
            required=False,
            widget=forms.HiddenInput(attrs={"autocomplete": "off"}),
        )
        self.fields["form_js"] = forms.CharField(
            required=False,
            widget=forms.HiddenInput(
                attrs={
                    "autocomplete": "off",
                    "tabindex": "-1",
                    "data-form-js": "1",
                }
            ),
        )
        if turnstile_enabled():
            # Widget injects this input; the field only reads the posted token.
            self.fields["cf-turnstile-response"] = forms.CharField(
                required=False,
                widget=forms.HiddenInput(attrs={"autocomplete": "off"}),
            )
        if not self.is_bound:
            self.fields["form_guard"].initial = issue_guard_token()

    def clean_form_guard(self):
        return (self.cleaned_data.get("form_guard") or "").strip()

    def clean_form_js(self):
        return (self.cleaned_data.get("form_js") or "").strip()

    def clean(self):
        cleaned = super().clean()
        if self.errors:
            return cleaned

        token = cleaned.get("form_guard") or ""
        reason = validate_guard_token(token)
        if reason:
            logger.info("Form guard rejected (%s) scope=%s", reason, self.antispam_scope)
            raise forms.ValidationError(self.antispam_reject_message)
        if not validate_js_proof(token, cleaned.get("form_js") or ""):
            logger.info("Form JS proof rejected scope=%s", self.antispam_scope)
            raise forms.ValidationError(self.antispam_reject_message)

        if turnstile_enabled():
            turnstile_token = cleaned.get("cf-turnstile-response") or ""
            ip = client_ip(self.request) if self.request is not None else None
            if not verify_turnstile(turnstile_token, ip):
                logger.info("Turnstile rejected scope=%s", self.antispam_scope)
                raise forms.ValidationError(self.antispam_reject_message)

        name = cleaned.get("name") or ""
        if name_flood_limited(name, scope=self.antispam_scope):
            logger.info("Name flood rejected scope=%s", self.antispam_scope)
            raise forms.ValidationError(self.antispam_reject_message)

        message = cleaned.get("message") or ""
        if message and message_flood_limited(message, scope=self.antispam_scope):
            logger.info("Message flood rejected scope=%s", self.antispam_scope)
            raise forms.ValidationError(self.antispam_reject_message)

        mark_guard_used(token)
        return cleaned


class ContactForm(AntiSpamFormMixin, forms.ModelForm):
    """Public contact form — fields map 1:1 to ContactMessage, plus spam guards.

    Adjust: keep label/autocomplete in sync with the contact template.
    Honeypot "website" must stay off-screen (see .hp-field in style.css).
    """

    antispam_scope = "kontakt"

    website = forms.CharField(
        required=False,
        label="Webbplats",
        widget=forms.TextInput(
            attrs={
                "tabindex": "-1",
                "autocomplete": "off",
                "aria-hidden": "true",
            }
        ),
    )

    class Meta:
        model = ContactMessage
        fields = ("name", "email", "phone", "subject", "message")
        labels = {
            "name": "Namn",
            "email": "E-post",
            "phone": "Telefon (valfritt)",
            "subject": "Ämne (valfritt)",
            "message": "Meddelande",
        }
        widgets = {
            "name": forms.TextInput(attrs={"autocomplete": "name"}),
            "email": forms.EmailInput(attrs={"autocomplete": "email"}),
            "phone": TelInput(attrs={"autocomplete": "tel"}),
            "subject": forms.TextInput(attrs={"autocomplete": "off"}),
            "message": forms.Textarea(attrs={"rows": 5, "autocomplete": "off"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Rule: name, email, message required for a usable contact path.
        self.fields["name"].required = True
        self.fields["message"].required = True
        configure_email_field(self.fields["email"])
        configure_phone_field(self.fields["phone"], required=False)
        hidden_names = {"website", "form_guard", "form_js", "cf-turnstile-response"}
        for name, field in self.fields.items():
            if name in hidden_names:
                continue
            field.widget.attrs["class"] = "form-control"
            if field.required:
                field.widget.attrs["aria-required"] = "true"
                field.widget.attrs["required"] = True
            # Link field errors for screen readers when present.
            if self.is_bound and self.errors.get(name):
                field.widget.attrs["aria-invalid"] = "true"
                field.widget.attrs["aria-describedby"] = f"error_{name}"

    def clean_email(self):
        """Normalize and re-check e-post format with a clear Swedish error."""
        email = (self.cleaned_data.get("email") or "").strip()
        EmailValidator(message=EMAIL_INVALID_MSG)(email)
        return email

    def clean_phone(self):
        """Telefon: digits only (optional field)."""
        return clean_digits_only(self.cleaned_data.get("phone"), required=False)

    def clean_website(self):
        """Honeypot. A filled value is rejected in clean() so the alert stays visible."""
        return (self.cleaned_data.get("website") or "").strip()

    def clean(self):
        """Drop submissions that filled the hidden website field."""
        if (self.data.get("website") or "").strip():
            logger.info("Honeypot rejected scope=%s", self.antispam_scope)
            raise forms.ValidationError(self.antispam_reject_message)
        return super().clean()
