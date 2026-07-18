"""Contact form submissions stored for staff review in admin."""

from django.db import models


class ContactMessage(models.Model):
    """One message from the public contact form.

    Adjust: add/remove fields here, in ContactForm, and in contact.html together.
    """

    class Status(models.TextChoices):
        NEW = "new", "Ny"
        READ = "read", "Läst"
        ARCHIVED = "archived", "Arkiverad"

    name = models.CharField(max_length=120)
    email = models.EmailField()
    phone = models.CharField(max_length=40, blank=True)
    subject = models.CharField(max_length=200, blank=True)
    message = models.TextField()
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.NEW,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "kontaktmeddelande"
        verbose_name_plural = "kontaktmeddelanden"

    def __str__(self):
        return f"{self.name} – {self.subject or 'Meddelande'} ({self.created_at:%Y-%m-%d})"
