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


def notify_ticket_reply(ticket, actor, message_body):
    """Create in-app and email notifications for a new ticket reply."""
    recipient_ids = {ticket.created_by_id}
    recipient_ids.update(ticket.participants.values_list("user_id", flat=True))
    recipient_ids.update(
        ticket.get_department_staff().values_list("id", flat=True)
    )
    recipient_ids.discard(getattr(actor, "id", None))

    recipients = User.objects.filter(id__in=recipient_ids, is_active=True)
    for recipient in recipients:
        create_notification(
            user=recipient,
            actor=actor,
            notification_type=Notification.NotificationType.TICKET_REPLY,
            target_object=ticket,
            link=f"/tickets/{ticket.uuid}/",
        )

        if recipient.email:
            send_mail(
                subject=f"[ResolveMe] New response on: {ticket.title}",
                message=(
                    f"Hi {recipient.get_full_name() or recipient.username},\n\n"
                    f"{actor.get_full_name() or actor.username} replied to "
                    f"ticket \"{ticket.title}\".\n\n"
                    f"{message_body}\n\n"
                    f"Open ticket: /tickets/{ticket.uuid}/"
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[recipient.email],
                fail_silently=True,
            )
