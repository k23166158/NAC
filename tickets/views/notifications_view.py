from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect, render
from tickets.models.notification import Notification


class NotificationView(LoginRequiredMixin, View):
    """View to display user notifications. Requires the user to be logged in."""
    template_name = "notifications.html"

    def get(self, request):
        """Handle GET requests to display the notifications page."""
        notifications = Notification.objects.filter(user=request.user)
        return render(request, self.template_name, {"notifications": notifications})


class NotificationOpenView(LoginRequiredMixin, View):
    """Mark a notification as read and redirect to its target if available."""

    def get(self, request, notification_id):
        notification = get_object_or_404(
            Notification,
            id=notification_id,
            user=request.user,
        )
        if not notification.is_read:
            notification.is_read = True
            notification.save(update_fields=["is_read", "updated_at"])

        ticket = notification.target_object
        if ticket and hasattr(ticket, "uuid"):
            return redirect("ticket_thread", uuid=ticket.uuid)
        return redirect("notifications")
