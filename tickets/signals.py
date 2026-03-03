from django.db.models.signals import post_save
from django.dispatch import receiver
from tickets.models.ticket import Ticket
from tickets.models.notification import Notification
from tickets.helpers.notifications import create_notification

@receiver(post_save, sender=Ticket)
def create_message_notification(sender, instance, created, **kwargs):
    """
    Triggered whenever a Ticket is saved
    If the ticket is newly created, it creates a notification for the ticket's participants.
    """
    if created:
        create_notification(
            user=instance.created_by,
            actor=instance.created_by,
            notification_type=Notification.NotificationType.TICKET_CREATED,
            target_object=instance,
            link=f"/tickets/{instance.uuid}/"
        )     
