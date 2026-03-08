from django.db import models
from django.conf import settings
from django.shortcuts import get_object_or_404
from .user_departments import UserDepartments
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

    @classmethod
    def pending_for_user(cls, user):
        """Return pending invitations for a user."""
        return cls.objects.filter(
            recipient=user,
            status='pending',
        ).select_related('department', 'sender').order_by('-created_at')

    @classmethod
    def process_action_for_user(cls, *, user, invite_id, action):
        """Accept or decline a pending invite for user, returning a message tuple."""
        if not invite_id or not action:
            return ("error", "Invalid request.")

        invite = get_object_or_404(
            cls,
            pk=invite_id,
            recipient=user,
            status='pending',
        )

        if action == 'accept':
            invite.status = 'accepted'
            invite.save(update_fields=['status'])
            UserDepartments.objects.get_or_create(
                user=user,
                department=invite.department,
            )
            return ("success", f'You have joined the department "{invite.department.name}".')

        if action == 'decline':
            invite.status = 'declined'
            invite.save(update_fields=['status'])
            return ("info", f'You have declined the invitation to "{invite.department.name}".')

        return ("error", "Invalid action.")