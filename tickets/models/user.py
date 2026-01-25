from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    """Model used for user authentication."""

    email = models.EmailField(unique=True, blank=False)
    
    first_name = models.CharField(max_length=50, blank=False)    

    last_name = models.CharField(max_length=50, blank=False)

    profile_picture = models.ImageField(upload_to='profile_pictures/', blank=True, null=True, help_text='User profile picture')

    bio = models.CharField(max_length=500, blank=True)

    class Meta:
        """Meta class for User model."""
        ordering = ["last_name", "first_name"]

    def full_name(self):
        """Return a string containing the user’s full name."""
        return f"{self.first_name} {self.last_name}"
    