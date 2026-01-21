from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    first_name = models.VarcharField(max_length=30, not_null=True)
    last_name = models.VarcharField(max_length=30, not_null=True)
    email = models.VarcharField(max_length=30, not_null=True)
    # profile_picture = models.ImageField(upload_to='profile_pics/', null=True, blank=True)
    date_joined = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)