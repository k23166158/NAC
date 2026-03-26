from django.contrib.auth.models import AnonymousUser

from tickets.models.notification import Notification


def unread_notifications(request):
    """
    Add the count of unread notifications for the current user to all templates.

    A notification is considered "yours" when you are the recipient. This matches
    the behaviour of the notifications page, which shows items where
    Notification.user == request.user.
    """
    user = getattr(request, "user", None)

    if not user or isinstance(user, AnonymousUser) or not user.is_authenticated:
        return {"unread_notification_count": 0}

    count = Notification.objects.filter(user=user, is_read=False).count()
    return {"unread_notification_count": count}

