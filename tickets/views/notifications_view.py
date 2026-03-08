from urllib import request
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render

from tickets.models.notification import Notification


class NotificationView(LoginRequiredMixin, View):
    """View to display user notifications. Requires the user to be logged in."""

    template_name = "notifications.html"

    def get(self, request):
        """Handle GET requests to display the notifications page."""
        qs = (Notification.objects.filter(user=request.user).select_related("actor", "user").order_by("is_read", "-created_at"))
        notifications = list(qs)
        Notification.objects.filter(user=request.user, is_read=False).update(
            is_read=True
        )
        return render(
            request,
            self.template_name,
            {"notifications": notifications},
        )