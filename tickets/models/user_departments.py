from django.db import models

from resolveme import settings
from .department import Department

class UserDepartments(models.Model):
    """Represents the assignment of a user to a specific department."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='user'
    )

    department = models.ForeignKey(
        Department,
        on_delete=models.CASCADE,
        related_name='assigned_users'
    )

    class Meta:
        """Meta options for the UserDepartments model."""
        db_table = "user_departments"
        verbose_name_plural = "User Departments"
        unique_together = ('user', 'department')

    def __str__(self):
        """String representation of the UserDepartments instance."""
        return f"Assignment: User {self.user.username} -> {self.department.name}"