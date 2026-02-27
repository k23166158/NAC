from django.db import models
from django.conf import settings
from .department import Department


class DepartmentInvitation(models.Model):
    """Model representing an invitation to join a department."""

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('declined', 'Declined'),
    ]

    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='sent_invitations'
    )

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='received_invitations'
    )

    department = models.ForeignKey(
        Department,
        on_delete=models.CASCADE,
        related_name='invitations'
    )

    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        """Order and uniqueness for department invitations."""
        ordering = ['-created_at']
        unique_together = ('department', 'recipient', 'status')

    def __str__(self):
        """Return a short string description of the invitation."""
        return f"Invite: {self.department.name} -> {self.recipient.username} ({self.status})"