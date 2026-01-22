from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """Model used for user authentication."""

    # changed default unique=False to True, default blank=True to False
    email = models.EmailField(unique=True, blank=False)
    # changed default blank=True to False
    first_name = models.CharField(max_length=50, blank=False)
    # changed default blank=True to False
    last_name = models.CharField(max_length=50, blank=False)

    bio = models.CharField(max_length=500, blank=True)

    class Meta:
        ordering = ["last_name", "first_name"]

    def full_name(self):
        """Return a string containing the user’s full name."""
        return f"{self.first_name} {self.last_name}"