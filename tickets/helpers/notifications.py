from django.template.loader import render_to_string
from django.conf import settings
from django.core.mail import send_mail
from tickets.models.notification import Notification
from tickets.models.user import User


def create_notification(user, actor, notification_type, link=None, target_object=None):
    """Factory function to create, render, and save a notification."""

    context = {'user': user, 'actor': actor, 'target': target_object, 'link': link}
    type_slug = notification_type.lower()
    short_template = f"notifications/{type_slug}_short.txt"
    long_template = f"notifications/{type_slug}_long.txt"

    short_message = render_to_string(short_template, context).strip()
    long_message = render_to_string(long_template, context).strip()

    return Notification.objects.create(
        user=user, actor=actor, target_object=target_object,
        notification_type=notification_type,
        short_message=short_message, long_message=long_message
    )


def _ticket_reply_recipient_ids(ticket, actor):
    """Return recipient ids for a ticket reply event."""
    recipient_ids = {ticket.created_by_id}
    recipient_ids.update(ticket.participants.values_list("user_id", flat=True))
    recipient_ids.update(ticket.get_department_staff().values_list("id", flat=True))
    recipient_ids.discard(getattr(actor, "id", None))
    return recipient_ids


def _reply_email_message(recipient, actor, ticket, message_body):
    """Build plain-text email body for ticket reply notifications."""
    actor_name = actor.get_full_name() or actor.username
    recipient_name = recipient.get_full_name() or recipient.username
    return (
        f"Hi {recipient_name},\n\n"
        f"{actor_name} replied to ticket \"{ticket.title}\".\n\n"
        f"{message_body}\n\n"
        f"Open ticket: /tickets/{ticket.uuid}/"
    )


def _create_reply_notifications(recipients, ticket, actor):
    """Create in-app reply notifications for recipients."""
    for recipient in recipients:
        create_notification(
            user=recipient,
            actor=actor,
            notification_type=Notification.NotificationType.TICKET_REPLY,
            target_object=ticket,
            link=f"/tickets/{ticket.uuid}/",
        )


def _send_reply_emails(recipients, ticket, actor, message_body):
    """Send reply emails to recipients with an email address."""
    for recipient in recipients.filter(email__isnull=False).exclude(email=""):
        send_mail(
            subject=f"[ResolveMe] New response on: {ticket.title}",
            message=_reply_email_message(recipient, actor, ticket, message_body),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[recipient.email],
            fail_silently=True,
        )


def notify_ticket_reply(ticket, actor, message_body):
    """Create in-app and email notifications for a new ticket reply."""
    recipient_ids = _ticket_reply_recipient_ids(ticket, actor)
    recipients = User.objects.filter(id__in=recipient_ids, is_active=True)
    _create_reply_notifications(recipients, ticket, actor)
    _send_reply_emails(recipients, ticket, actor, message_body)
