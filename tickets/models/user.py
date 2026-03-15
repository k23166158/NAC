from django.contrib.auth.models import AbstractUser
from django.db.models import Count, Q
from django.db import models
from django.shortcuts import get_object_or_404
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

    @classmethod
    def get_by_pk_or_404(cls, pk):
        """Return a user by primary key or raise 404."""
        return get_object_or_404(cls, pk=pk)

    def has_management_access(self):
        """Return whether this user can access management pages."""
        return self.is_staff or self.is_superuser

    @classmethod
    def managed_queryset(cls, search_query=""):
        """Return user-management queryset with department counts and search."""
        queryset = cls.objects.annotate(department_count=Count("user"))
        queryset = cls._apply_management_search(queryset, search_query)
        return queryset.order_by("-is_superuser", "-is_staff", "last_name", "first_name")

    @staticmethod
    def _apply_management_search(queryset, search_query):
        """Filter user-management queryset by search query when provided."""
        if not search_query:
            return queryset
        return queryset.filter(
            Q(username__icontains=search_query)
            | Q(first_name__icontains=search_query)
            | Q(last_name__icontains=search_query)
            | Q(email__icontains=search_query)
        )

    def can_toggle_user(self, target_user):
        """Return whether this user may toggle active status for target user."""
        if target_user == self:
            return False
        if self.is_superuser:
            return True
        return self.is_staff and not (target_user.is_staff or target_user.is_superuser)

    def toggle_user_active(self, target_user):
        """Toggle active state of target user when allowed."""
        if not self.can_toggle_user(target_user):
            return False
        target_user.is_active = not target_user.is_active
        target_user.save(update_fields=["is_active"])
        return True

    @classmethod
    def top_ticket_creators(cls, *, limit=5):
        """Return top ticket creators as dictionaries."""
        return list(
            cls.objects.annotate(ticket_count=Count("tickets_created", distinct=True))
            .order_by("-ticket_count")
            .values("username", "ticket_count")[:limit]
        )

    @classmethod
    def top_staff_responders(cls, *, limit=5):
        """Return top staff responders as dictionaries."""
        return list(
            cls.objects.filter(is_staff=True)
            .annotate(msgs=Count("ticket_messages", distinct=True))
            .order_by("-msgs")
            .values("username", "msgs")[:limit]
        )

    @classmethod
    def admin_user_stats(cls):
        """Return admin user statistics payload."""
        return {
            "top_creators": cls.top_ticket_creators(),
            "top_responders": cls.top_staff_responders(),
        }

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
