from django.core.mail import send_mail
from django.template.loader import render_to_string
from tickets.models.notification import Notification

def create_notification(user, actor, notification_type, link=None, target_object=None):
    """Factory function to create, render, and save a notification."""

    context = {'user': user, 'actor': actor, 'target': target_object, 'link': link}
    type_slug = notification_type.lower()
    short_template = f"notifications/{type_slug}_short.txt"
    long_template = f"notifications/{type_slug}_long.txt"

    short_message = render_to_string(short_template, context).strip()
    long_message = render_to_string(long_template, context).strip()

    send_email(user, short_message, long_message)
    return Notification.objects.create(
        user=user, actor=actor, target_object=target_object,
        notification_type=notification_type, short_message=short_message
    )

def send_email(user, short_message, long_message):
    """Sends an email using Django's built-in mail utility."""
    send_mail(
        subject=short_message,
        message=long_message,
        from_email="noreply@example.com",
        recipient_list=[user.email],
        fail_silently=False, 
    )