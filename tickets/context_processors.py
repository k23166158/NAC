from tickets.models.notification import Notification


def notifications_context(request):
    """Return unread notification count for the authenticated user."""
    if not request.user.is_authenticated:
        return {"unread_notifications_count": 0}

    return {
        "unread_notifications_count": Notification.objects.filter(
            user=request.user,
            is_read=False,
        ).count()
    }
