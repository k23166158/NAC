from django.shortcuts import render
from django.views import View
from django.contrib.auth.mixins import UserPassesTestMixin

from tickets.models import Ticket, User


class AdminStatisticsView(UserPassesTestMixin, View):
    """View to display admin statistics for tickets and users."""
    raise_exception = True

    def test_func(self) -> bool:
        """Check if user has access."""
        return self.request.user.has_management_access()

    def get(self, request):
        """Handle GET requests for admin statistics."""
        context = {
            "ticket_stats": Ticket.admin_ticket_stats(),
            "user_stats": User.admin_user_stats(),
        }
        return render(request, "admin_statistics.html", context)
