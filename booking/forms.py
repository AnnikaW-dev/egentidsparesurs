"""Forms for public booking and staff availability tools."""

import json

from django import forms
from django.core.exceptions import ValidationError
from django.core.validators import EmailValidator
from django.utils import timezone
from django.utils.safestring import mark_safe

from pages.forms import (
    EMAIL_INVALID_MSG,
    TelInput,
    clean_digits_only,
    configure_email_field,
    configure_phone_field,
)

from .models import (
    Booking,
    Service,
    WeeklyAvailability,
    slot_run_covering,
    upcoming_open_slots,
)


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


def _open_slots_by_day():
    """Map YYYY-MM-DD → [{id, time}] for upcoming open start slots."""
    grouped = {}
    for slot in upcoming_open_slots():
        local = timezone.localtime(slot.start)
        grouped.setdefault(local.date().isoformat(), []).append(
            {"id": slot.pk, "time": local.strftime("%H:%M")}
        )
    return grouped


class BookingDateInput(forms.DateInput):
    """Native date picker plus JSON of open slots for the klockslag script."""

    input_type = "date"

    def __init__(self, attrs=None, slots_by_day=None):
        super().__init__(attrs)
        self.slots_by_day = slots_by_day or {}

    def render(self, name, value, attrs=None, renderer=None):
        html = super().render(name, value, attrs, renderer)
        payload = json.dumps(self.slots_by_day, separators=(",", ":"))
        return mark_safe(
            f"{html}"
            f'<script type="application/json" id="staff-booking-slots">{payload}</script>'
        )


class StaffBookingForm(forms.ModelForm):
    """Admin add-form: pick treatment, date, time, and customer details.

    Occupies treatment length plus 30 minutes, same as public /boka/.
    """

    booking_date = forms.DateField(
        label="Datum",
        help_text="Välj dag i kalendern. Lediga klockslag för den dagen visas under Klockslag.",
    )
    booking_time = forms.ChoiceField(
        label="Klockslag",
        choices=(("", "Välj tid"),),
        help_text="Lediga starter den valda dagen. Behandlingstiden plus 30 minuter reserveras.",
    )

    class Meta:
        model = Booking
        fields = (
            "service",
            "booking_date",
            "booking_time",
            "customer_name",
            "customer_email",
            "customer_phone",
            "notify_email",
            "notify_sms",
            "notes",
        )
        labels = {
            "service": "Behandling",
            "customer_name": "Kundens namn",
            "customer_email": "E-post",
            "customer_phone": "Telefonnummer",
            "notify_email": "Skicka bekräftelse med e-post",
            "notify_sms": "Skicka bekräftelse med SMS",
            "notes": "Intern anteckning",
        }
        help_texts = {
            "notes": "Syns bara här i admin, inte för kunden.",
        }
        widgets = {
            "customer_name": forms.TextInput(attrs={"autocomplete": "name"}),
            "customer_email": forms.EmailInput(
                attrs={"autocomplete": "email", "inputmode": "email"}
            ),
            "customer_phone": TelInput(
                attrs={"autocomplete": "tel", "data-phone-digits-only": "true"}
            ),
            "notes": forms.Textarea(attrs={"rows": 3}),
        }

    class Media:
        js = ["js/admin-staff-booking.js"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from .models import TimeSlot

        self.slots_by_day = _open_slots_by_day()
        self.fields["service"].queryset = Service.objects.filter(is_active=True)
        self.fields["service"].empty_label = "Välj behandling"

        days = sorted(self.slots_by_day)
        date_attrs = {"autocomplete": "off", "aria-required": "true"}
        if days:
            date_attrs["min"] = days[0]
            date_attrs["max"] = days[-1]
        else:
            self.fields["booking_date"].help_text = (
                "Inga lediga tider finns just nu. Öppna Veckoschema / öppettider, "
                "bocka i Aktiv för de dagar ni tar emot kunder, och spara."
            )
        self.fields["booking_date"].widget = BookingDateInput(
            attrs=date_attrs,
            slots_by_day=self.slots_by_day,
        )

        slot_pk = self._posted_or_initial_slot_pk()
        slot = TimeSlot.objects.filter(pk=slot_pk).first() if slot_pk else None
        chosen_day = self._chosen_day_iso(slot)
        self.fields["booking_time"].choices = self._time_choices(chosen_day)
        if slot and not self.is_bound:
            local = timezone.localtime(slot.start)
            self.fields["booking_date"].initial = local.date()
            self.fields["booking_time"].initial = str(slot.pk)

        self.fields["booking_time"].widget.attrs["aria-required"] = "true"

        self.fields["customer_name"].required = True
        self.fields["customer_email"].required = True
        self.fields["customer_phone"].required = True
        configure_email_field(self.fields["customer_email"])
        configure_phone_field(self.fields["customer_phone"], required=True)
        self.fields["notify_email"].initial = True
        self.fields["notify_sms"].initial = True
        for name in ("customer_name", "customer_email", "customer_phone"):
            self.fields[name].widget.attrs["aria-required"] = "true"

    def _posted_or_initial_slot_pk(self):
        """Slot id from posted klockslag or from ?slot= on the add URL."""
        if self.data.get("booking_time"):
            return self.data.get("booking_time")
        slot = self.initial.get("slot")
        if slot is None:
            return None
        return str(getattr(slot, "pk", slot))

    def _chosen_day_iso(self, slot):
        """ISO date from POST, initial date, or the pre-selected slot."""
        raw = self.data.get("booking_date") or self.initial.get("booking_date")
        if raw:
            return str(raw)
        if slot:
            return timezone.localtime(slot.start).date().isoformat()
        return ""

    def _time_choices(self, day_iso):
        """Times for one day, or all days labelled with date (no-JS fallback)."""
        empty = ("", "Välj tid")
        if day_iso and day_iso in self.slots_by_day:
            return [empty] + [
                (str(item["id"]), item["time"]) for item in self.slots_by_day[day_iso]
            ]
        choices = [empty]
        for day, items in self.slots_by_day.items():
            for item in items:
                choices.append((str(item["id"]), f"{day} {item['time']}"))
        return choices

    def clean_customer_email(self):
        """Same e-post rules as the public booking form."""
        email = (self.cleaned_data.get("customer_email") or "").strip()
        EmailValidator(message=EMAIL_INVALID_MSG)(email)
        return email

    def clean_customer_phone(self):
        """Digits only, same length checks as the public form."""
        digits = clean_digits_only(self.cleaned_data.get("customer_phone"), required=True)
        if len(digits) < 7:
            raise ValidationError("Telefonnumret måste vara minst 7 siffror.")
        if len(digits) > 15:
            raise ValidationError("Telefonnumret får vara högst 15 siffror.")
        return digits

    def clean(self):
        """Resolve date + klockslag to a slot that fits treatment plus buffer."""
        from .models import TimeSlot

        cleaned = super().clean()
        booking_date = cleaned.get("booking_date")
        time_pk = cleaned.get("booking_time")
        slot = None
        if time_pk:
            slot = TimeSlot.objects.filter(pk=time_pk).first()
            if slot is None:
                self.add_error("booking_time", "Välj ett ledigt klockslag.")
            elif booking_date and timezone.localtime(slot.start).date() != booking_date:
                self.add_error(
                    "booking_time",
                    "Klockslaget hör inte till det valda datumet. Välj tiden igen.",
                )
                slot = None
        if booking_date and not time_pk:
            self.add_error("booking_time", "Välj ett klockslag för det datumet.")
        service = cleaned.get("service")
        if service and slot and not slot_run_covering(slot, service.calendar_minutes()):
            self.add_error(
                "booking_time",
                "Den tiden räcker inte för behandlingen, eller är inte ledig. "
                "Välj en tidigare start, eller en kortare behandling.",
            )
            slot = None
        cleaned["slot"] = slot
        return cleaned

    def save(self, commit=True):
        """Create the booking and occupy consecutive slots (ignores commit=False)."""
        from .models import create_confirmed_booking

        data = self.cleaned_data
        booking = create_confirmed_booking(
            service=data["service"],
            start_slot=data["slot"],
            customer_name=data["customer_name"],
            customer_email=data["customer_email"],
            customer_phone=data["customer_phone"],
            notify_email=data.get("notify_email", False),
            notify_sms=data.get("notify_sms", False),
            notes=data.get("notes") or "",
        )
        self.instance = booking
        self.save_m2m = lambda: None
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
