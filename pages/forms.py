"""Forms for public pages (contact) — labels, autocomplete, a11y attrs."""

from django import forms

from .models import ContactMessage


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
            "phone": forms.TextInput(attrs={"autocomplete": "tel"}),
            "subject": forms.TextInput(attrs={"autocomplete": "off"}),
            "message": forms.Textarea(attrs={"rows": 5, "autocomplete": "off"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Rule: name, email, message required for a usable contact path.
        self.fields["name"].required = True
        self.fields["email"].required = True
        self.fields["message"].required = True
        for name, field in self.fields.items():
            field.widget.attrs["class"] = "form-control"
            if field.required:
                field.widget.attrs["aria-required"] = "true"
                field.widget.attrs["required"] = True
            # Link field errors for screen readers when present.
            if self.is_bound and self.errors.get(name):
                field.widget.attrs["aria-invalid"] = "true"
                field.widget.attrs["aria-describedby"] = f"error_{name}"
