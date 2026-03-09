from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View

from tickets.models.notification import Notification


class NotificationView(LoginRequiredMixin, View):
    """View to display user notifications."""

    template_name = 'notifications.html'

    def get(self, request):
        """Render the notifications page for the current user."""
        qs = Notification.objects.filter(user=request.user).select_related('actor', 'user')
        notifications = list(qs.order_by('is_read', '-created_at'))
        return render(request, self.template_name, {'notifications': notifications})


class NotificationOpenView(LoginRequiredMixin, View):
    """Mark one notification as read and redirect to its destination."""

    def get(self, request, notification_id):
        """Open a notification and redirect to ticket thread when available."""
        notification = get_object_or_404(Notification, id=notification_id, user=request.user)
        if not notification.is_read:
            notification.is_read = True
            notification.save(update_fields=['is_read', 'updated_at'])
        ticket = notification.target_object
        if ticket and hasattr(ticket, 'uuid'):
            return redirect('ticket_thread', uuid=ticket.uuid)
        return redirect('notifications')
