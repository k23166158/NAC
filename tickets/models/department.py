from django.conf import settings
from django.db import models

class Department(models.Model):
    """Model representing a department within the ticketing system."""
    name = models.CharField(max_length=255)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="departments_created",
    )

    created_on = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        """String representation of the Department model."""
        return self.name

    class Meta:
        """Meta options for the Department model."""
        ordering = ["name"]