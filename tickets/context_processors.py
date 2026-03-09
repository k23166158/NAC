from django.contrib.auth.models import AnonymousUser

from tickets.models.notification import Notification


def unread_notifications(request):
    """Add unread notification count for authenticated users."""
    user = getattr(request, 'user', None)
    if not user or isinstance(user, AnonymousUser) or not user.is_authenticated:
        return {'unread_notification_count': 0, 'unread_notifications_count': 0}
    count = Notification.objects.filter(user=user, is_read=False).count()
    return {'unread_notification_count': count, 'unread_notifications_count': count}


def notifications_context(request):
    """Backward-compatible alias for unread notifications context."""
    return unread_notifications(request)
