"""Forms for public booking and staff availability tools."""

from django import forms
from django.core.exceptions import ValidationError
from django.core.validators import EmailValidator

from pages.forms import (
    EMAIL_INVALID_MSG,
    TelInput,
    clean_digits_only,
    configure_email_field,
    configure_phone_field,
)

from .models import Booking, WeeklyAvailability


class BookingForm(forms.ModelForm):
    """Step 3: name, email, phone, and how to send the confirmation."""

    CONFIRM_CHOICES = (
        ("email", "E-post"),
        ("sms", "SMS"),
    )

    confirm_via = forms.MultipleChoiceField(
        label="Hur vill du få din bekräftelse?",
        choices=CONFIRM_CHOICES,
        widget=forms.CheckboxSelectMultiple,
        initial=["email", "sms"],
        required=True,
        error_messages={"required": "Välj e-post, SMS eller båda."},
        help_text="Välj minst ett alternativ. Du kan få bekräftelsen på e-post, som SMS, eller båda.",
    )

    class Meta:
        model = Booking
        fields = ("customer_name", "customer_email", "customer_phone")
        labels = {
            "customer_name": "Fullständigt namn",
            "customer_email": "E-post",
            "customer_phone": "Telefonnummer",
        }
        widgets = {
            "customer_name": forms.TextInput(attrs={"autocomplete": "name"}),
            "customer_email": forms.EmailInput(
                attrs={
                    "autocomplete": "email",
                    "inputmode": "email",
                }
            ),
            "customer_phone": TelInput(
                attrs={
                    "autocomplete": "tel",
                    "data-phone-digits-only": "true",
                }
            ),
        }

    def __init__(self, *args, service=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.service = service
        self.fields["customer_name"].required = True
        self.fields["customer_email"].required = True
        self.fields["customer_phone"].required = True
        configure_email_field(self.fields["customer_email"])
        configure_phone_field(self.fields["customer_phone"], required=True)
        self.fields["confirm_via"].widget.attrs["class"] = "confirm-via-list"
        for name, field in self.fields.items():
            if name == "confirm_via":
                continue
            field.widget.attrs["class"] = "form-control"
            field.widget.attrs["aria-required"] = "true"
            field.widget.attrs["required"] = True
            if self.is_bound and self.errors.get(name):
                field.widget.attrs["aria-invalid"] = "true"
                if name == "customer_phone":
                    field.widget.attrs["aria-describedby"] = "phone_hint error_customer_phone"
                else:
                    field.widget.attrs["aria-describedby"] = f"error_{name}"
        if "customer_phone" in self.fields and not self.errors.get("customer_phone"):
            self.fields["customer_phone"].widget.attrs.setdefault(
                "aria-describedby", "phone_hint"
            )
        described_by = ["confirm_via_hint"]
        if self.is_bound and self.errors.get("confirm_via"):
            described_by.append("error_confirm_via")
        self.fields["confirm_via"].widget.attrs["aria-describedby"] = " ".join(described_by)
        self.fields["confirm_via"].widget.attrs["aria-invalid"] = (
            "true" if self.is_bound and self.errors.get("confirm_via") else "false"
        )

    def clean_customer_email(self):
        """Normalize and re-check e-post format with a clear Swedish error."""
        email = (self.cleaned_data.get("customer_email") or "").strip()
        EmailValidator(message=EMAIL_INVALID_MSG)(email)
        return email

    def clean_customer_phone(self):
        """Accept digits only — strip anything pasted with spaces or dashes."""
        digits = clean_digits_only(self.cleaned_data.get("customer_phone"), required=True)
        if len(digits) < 7:
            raise ValidationError("Telefonnumret måste vara minst 7 siffror.")
        if len(digits) > 15:
            raise ValidationError("Telefonnumret får vara högst 15 siffror.")
        return digits

    def save(self, commit=True):
        """Copy confirm_via checkboxes onto notify_email / notify_sms."""
        booking = super().save(commit=False)
        chosen = set(self.cleaned_data.get("confirm_via") or [])
        booking.notify_email = "email" in chosen
        booking.notify_sms = "sms" in chosen
        if commit:
            booking.save()
        return booking


class AvailabilityGenerateForm(forms.Form):
    """Generate materialized slots for one week or one calendar month."""

    MODE_CHOICES = (
        ("week", "En vecka (7 dagar från startdatum)"),
        ("month", "Kalendermånad (från startdatum till månadens slut)"),
    )

    start_date = forms.DateField(
        label="Startdatum",
        widget=forms.DateInput(attrs={"type": "date", "class": "form-control"}),
    )
    mode = forms.ChoiceField(
        label="Period",
        choices=MODE_CHOICES,
        widget=forms.Select(attrs={"class": "form-control"}),
    )


class QuickWeekForm(forms.Form):
    """Edit Mon–Sun open hours and default slot length in one form."""

    slot_minutes = forms.IntegerField(
        label="Passlängd (minuter)",
        min_value=15,
        max_value=240,
        initial=60,
        widget=forms.NumberInput(attrs={"class": "form-control"}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        existing = {
            w.weekday: w for w in WeeklyAvailability.objects.filter(is_active=True)
        }
        for weekday, label in WeeklyAvailability.WEEKDAYS:
            rule = existing.get(weekday)
            self.fields[f"day_{weekday}_enabled"] = forms.BooleanField(
                label=label,
                required=False,
                initial=bool(rule),
            )
            self.fields[f"day_{weekday}_start"] = forms.TimeField(
                label=f"{label} från",
                required=False,
                initial=rule.start_time if rule else "09:00",
                widget=forms.TimeInput(attrs={"type": "time", "class": "form-control"}),
            )
            self.fields[f"day_{weekday}_end"] = forms.TimeField(
                label=f"{label} till",
                required=False,
                initial=rule.end_time if rule else "17:00",
                widget=forms.TimeInput(attrs={"type": "time", "class": "form-control"}),
            )
            self.fields[f"day_{weekday}_enabled"].widget.attrs["aria-label"] = (
                f"Öppen {label.lower()}"
            )
            self.fields[f"day_{weekday}_start"].widget.attrs["aria-label"] = (
                f"{label} öppnar"
            )
            self.fields[f"day_{weekday}_end"].widget.attrs["aria-label"] = (
                f"{label} stänger"
            )
            self.fields[f"day_{weekday}_lunch_start"] = forms.TimeField(
                label=f"{label} lunch från",
                required=False,
                initial=rule.lunch_start if rule else None,
                widget=forms.TimeInput(attrs={"type": "time", "class": "form-control"}),
            )
            self.fields[f"day_{weekday}_lunch_end"] = forms.TimeField(
                label=f"{label} lunch till",
                required=False,
                initial=rule.lunch_end if rule else None,
                widget=forms.TimeInput(attrs={"type": "time", "class": "form-control"}),
            )
            self.fields[f"day_{weekday}_lunch_start"].widget.attrs["aria-label"] = (
                f"{label} lunch från"
            )
            self.fields[f"day_{weekday}_lunch_end"].widget.attrs["aria-label"] = (
                f"{label} lunch till"
            )

    def clean(self):
        """Lunch is optional per day; both ends must be set and sit inside hours."""
        cleaned = super().clean()
        for weekday, label in WeeklyAvailability.WEEKDAYS:
            lunch_start = cleaned.get(f"day_{weekday}_lunch_start")
            lunch_end = cleaned.get(f"day_{weekday}_lunch_end")
            open_start = cleaned.get(f"day_{weekday}_start")
            open_end = cleaned.get(f"day_{weekday}_end")
            if bool(lunch_start) != bool(lunch_end):
                self.add_error(
                    f"day_{weekday}_lunch_start",
                    f"Ange både lunch från och till för {label.lower()}, eller lämna båda tomma.",
                )
                continue
            if lunch_start and lunch_end:
                if lunch_start >= lunch_end:
                    self.add_error(
                        f"day_{weekday}_lunch_end",
                        f"Lunch till måste vara efter lunch från på {label.lower()}.",
                    )
                elif open_start and open_end and (
                    lunch_start < open_start or lunch_end > open_end
                ):
                    self.add_error(
                        f"day_{weekday}_lunch_start",
                        f"Lunchen på {label.lower()} måste ligga inom öppettiderna.",
                    )
        return cleaned
