from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.text import slugify


class User(AbstractUser):
    """Model used for user authentication."""

    email = models.EmailField(unique=True, blank=False)
    first_name = models.CharField(max_length=50, blank=False)
    last_name = models.CharField(max_length=50, blank=False)
    profile_picture = models.ImageField(
        upload_to="profile_pictures/",
        blank=True,
        null=True,
        help_text="User profile picture",
    )
    bio = models.CharField(max_length=500, blank=True)

    profile_slug = models.SlugField(max_length=160, unique=True, blank=True)

    class Meta:
        """Meta class for User model."""
        ordering = ["last_name", "first_name"]

    def full_name(self):
        """Return a string containing the user’s full name."""
        return f"{self.first_name} {self.last_name}"

    def save(self, *args, **kwargs):
        """Save user and ensure profile_slug is set and unique."""
        if not self.profile_slug:
            self.profile_slug = self._build_unique_profile_slug()
        super().save(*args, **kwargs)

    def _build_unique_profile_slug(self):
        """Build a unique, URL-safe slug based on username."""
        base = slugify(self.username) or "user"
        slug = base
        i = 1
        while type(self).objects.filter(profile_slug=slug).exclude(pk=self.pk).exists():
            i += 1
            slug = f"{base}-{i}"
        return slug
