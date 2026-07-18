"""Forms for public booking and staff availability tools."""

from django import forms

from .models import Booking, Service, WeeklyAvailability


class BookingForm(forms.ModelForm):
    """Customer booking details for a selected time slot.

    Adjust: keep autocomplete and required flags in sync with book.html.
    """

    class Meta:
        model = Booking
        fields = ("service", "customer_name", "customer_email", "customer_phone", "notes")
        labels = {
            "service": "Behandling",
            "customer_name": "Namn",
            "customer_email": "E-post",
            "customer_phone": "Telefon",
            "notes": "Meddelande (valfritt)",
        }
        widgets = {
            "customer_name": forms.TextInput(attrs={"autocomplete": "name"}),
            "customer_email": forms.EmailInput(attrs={"autocomplete": "email"}),
            "customer_phone": forms.TextInput(attrs={"autocomplete": "tel"}),
            "notes": forms.Textarea(attrs={"rows": 3, "autocomplete": "off"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["service"].queryset = Service.objects.filter(is_active=True)
        self.fields["customer_name"].required = True
        self.fields["customer_email"].required = True
        self.fields["service"].required = True
        for name, field in self.fields.items():
            field.widget.attrs["class"] = "form-control"
            if field.required:
                field.widget.attrs["aria-required"] = "true"
                field.widget.attrs["required"] = True
            if self.is_bound and self.errors.get(name):
                field.widget.attrs["aria-invalid"] = "true"
                field.widget.attrs["aria-describedby"] = f"error_{name}"


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
