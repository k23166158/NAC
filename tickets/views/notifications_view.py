from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.paginator import Paginator
from django.shortcuts import render
from django.views import View

from tickets.models.notification import Notification


class NotificationView(LoginRequiredMixin, View):
    """View to display user notifications. Requires the user to be logged in."""

    template_name = "notifications.html"
    paginate_by = 10

    def get(self, request):
        """Handle GET requests to display the notifications page."""
        Notification.purge_expired_for(request.user)
        paginator = Paginator(Notification.recent_for_user(request.user), self.paginate_by)
        page_obj = paginator.get_page(request.GET.get("page", 1))
        Notification.mark_all_read_for(request.user)
        return render(
            request,
            self.template_name,
            {"notifications": page_obj.object_list, "page_obj": page_obj},
        )
