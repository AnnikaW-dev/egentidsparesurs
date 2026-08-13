"""Forms for public booking and staff availability tools."""

from django import forms

from .models import Booking, Service, WeeklyAvailability


class BookingForm(forms.ModelForm):
    """Step 3: customer name and phone for a pre-selected service and slot.

    Service is fixed before the form is shown; adjust labels in book.html.
    """

    class Meta:
        model = Booking
        fields = ("customer_name", "customer_phone")
        labels = {
            "customer_name": "Fullständigt namn",
            "customer_phone": "Telefonnummer",
        }
        widgets = {
            "customer_name": forms.TextInput(
                attrs={"autocomplete": "name", "placeholder": "För- och efternamn"}
            ),
            "customer_phone": forms.TextInput(
                attrs={"autocomplete": "tel", "placeholder": "07X XXX XX XX", "inputmode": "tel"}
            ),
        }

    def __init__(self, *args, service=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.service = service
        self.fields["customer_name"].required = True
        self.fields["customer_phone"].required = True
        for name, field in self.fields.items():
            field.widget.attrs["class"] = "form-control"
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
