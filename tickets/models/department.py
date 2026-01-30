from django.conf import settings
from django.db import models
from django.utils.text import slugify


class Department(models.Model):
    """Model representing a department within the ticketing system."""
    name = models.CharField(max_length=255)
    description = models.TextField(max_length=1023, blank=True, help_text='Description of the department')
    slug = models.SlugField(max_length=255, unique=True, blank=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="departments_created",
    )

    created_on = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        """Override save to generate a slug from the name."""
        self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        """String representation of the Department model."""
        return self.name

    class Meta:
        """Meta options for the Department model."""
        ordering = ["name"]