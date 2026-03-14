from django.db import models
from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType

class Notification(models.Model):
    """Represents a generic notification for various system events."""

    class NotificationType(models.TextChoices):
        """Defines the types of notifications that can be created."""
        TICKET_CREATED = 'TICKET_CREATED', 'Ticket Created'
        TICKET_CLOSED = 'TICKET_CLOSED', 'Ticket Closed'
        STAFF_ASSIGNED = 'STAFF_ASSIGNED', 'Staff Assigned'
        STAFF_REMOVED = 'STAFF_REMOVED', 'Staff Removed'
        DEPT_ASSIGNED = 'DEPT_ASSIGNED', 'Department Assigned'
        DEPT_REMOVED = 'DEPT_REMOVED', 'Department Removed'
        NEW_MESSAGE = 'NEW_MESSAGE', 'New Message'
        TICKET_FORWARDED = 'TICKET_FORWARDED', 'Ticket Forwarded'
        DEPT_INVITED = 'DEPT_INVITED', 'Department Invitation Sent'
        DEPT_MEMBER_REMOVED = 'DEPT_MEMBER_REMOVED', 'Removed From Department'
        DEPT_INVITE_ACCEPTED = 'DEPT_INVITE_ACCEPTED', 'Department Invite Accepted'
        DEPT_INVITE_DECLINED = 'DEPT_INVITE_DECLINED', 'Department Invite Declined'
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications'
    )

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='actions_triggered',
        null=True,
        blank=True
    )

    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, null=True, blank=True)
    object_id = models.PositiveIntegerField(null=True, blank=True)
    target_object = GenericForeignKey('content_type', 'object_id')

    notification_type = models.CharField(
        max_length=30,
        choices=NotificationType.choices
    )
    
    short_message = models.CharField(max_length=255)
    is_read = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        """Meta information for the Notification model."""
        ordering = ['-created_at']

    def __str__(self):
        """String representation of the Notification instance."""
        return f"{self.notification_type} for {self.user.username}"