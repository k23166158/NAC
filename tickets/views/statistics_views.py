from django.contrib.auth import get_user_model
from django.db.models import Count
from django.shortcuts import render
from django.views import View
from django.contrib.auth.mixins import UserPassesTestMixin

from tickets.models import Ticket

User = get_user_model()


class AdminStatisticsView(UserPassesTestMixin, View):
    """View to display admin statistics for tickets and users."""
    raise_exception = True

    def test_func(self) -> bool:
        """Check if user has access."""
        return self.request.user.is_superuser or self.request.user.is_staff

    def get(self, request):
        """Handle GET requests for admin statistics."""
        context = {
            "ticket_stats": self.get_ticket_stats(),
            "user_stats": self.get_user_stats(),
        }
        return render(request, "admin_statistics.html", context)

    def get_ticket_stats(self) -> dict:
        """Calculate overall ticket statistics."""
        total = Ticket.objects.count()
        open_count = Ticket.objects.filter(status=Ticket.Status.OPEN).count()
        pending = Ticket.objects.filter(status=Ticket.Status.PENDING).count()
        closed_count = Ticket.objects.filter(status=Ticket.Status.CLOSED).count()
        return {
            "total": total,
            "open": open_count,
            "pending": pending,
            "closed": closed_count,
        }

    def get_user_stats(self) -> dict:
        """Calculate statistics for top users (creators/responders)."""
        top_creators = User.objects.annotate(
            ticket_count=Count('tickets_created', distinct=True)
        ).order_by("-ticket_count")[:5]

        top_responders = User.objects.filter(is_staff=True).annotate(
            msgs=Count('ticket_messages', distinct=True)
        ).order_by("-msgs")[:5]

        return {
            "top_creators": list(top_creators.values("username", "ticket_count")),
            "top_responders": list(top_responders.values("username", "msgs")),
        }
