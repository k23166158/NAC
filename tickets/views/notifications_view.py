from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render

from tickets.models.notification import Notification


class NotificationView(LoginRequiredMixin, View):
    """View to display user notifications. Requires the user to be logged in."""

    template_name = "notifications.html"

    def get(self, request):
        """Handle GET requests to display the notifications page."""
        notifications = list(Notification.for_display_for(request.user))
        Notification.mark_all_read_for(request.user)
        return render(
            request,
            self.template_name,
            {"notifications": notifications},
        )
