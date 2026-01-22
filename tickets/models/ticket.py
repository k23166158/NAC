from django.db import models
from django.conf import settings


class Ticket(models.Model):
    """Represents a support ticket in the system."""

    class Status(models.TextChoices):
        """Represents the status of a support ticket."""
        OPEN = 'open', 'Open'
        PENDING = 'pending', 'Pending'
        CLOSED = 'closed', 'Closed'

    title = models.CharField(max_length=200)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.OPEN
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='tickets_created'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        """Returns a string representation of the ticket."""
        return f"#{self.id} - {self.title}"
