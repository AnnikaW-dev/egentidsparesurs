"""Forms for public pages (contact) — labels, autocomplete, a11y attrs."""

from django import forms
from django.core.validators import EmailValidator, RegexValidator

from .models import ContactMessage

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


class ContactForm(forms.ModelForm):
    """Public contact form — fields map 1:1 to ContactMessage.

    Adjust: keep label/autocomplete in sync with the contact template.
    """

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
        for name, field in self.fields.items():
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
