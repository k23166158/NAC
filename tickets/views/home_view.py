from django.shortcuts import render
from django.views import View

from tickets.models import Ticket, User


class HomeView(View):
    """View for the home page/dashboard."""

    def get(self, request):
        """Handle GET request for home page."""
        if not request.user.is_authenticated:
            return render(request, "unauthenticated_home.html")

        scope = request.GET.get("scope", "personal")
        qs, scope = self.handle_scope(request.user, scope)
        overdue = self.overdue_tickets(qs)

        ctx = self.get_context(request, qs, scope, overdue)
        if self.is_admin(request.user):
            ctx.update(self.get_admin_stats())

        return render(request, "home_view.html", ctx)

    def _get_page(self, request, queryset, param_name, per_page=10):
        """Helper method to return a paginated page."""
        from django.core.paginator import Paginator
        return Paginator(queryset, per_page).get_page(request.GET.get(param_name, 1))

    def get_context(self, request, qs, scope, overdue):
        """Build the base context dictionary for the view, with pagination for the lists."""
        active_qs = self.active_tickets(qs, overdue)
        completed_qs = self.completed_tickets(qs)

        return {
            "scope": scope,
            "completed_tickets": completed_qs,
            "overdue_tickets": overdue,
            "active_tickets": active_qs,
            "active_tickets_page": self._get_page(request, active_qs, 'active_page'),
            "overdue_tickets_page": self._get_page(request, overdue, 'overdue_page'),
            "completed_tickets_page": self._get_page(request, completed_qs, 'completed_page'),
        }

    def get_admin_stats(self):
        """Returns extra admin statistics for the dashboard."""
        return {
            "total_tickets": Ticket.objects.count(),
            "tickets_by_status": self.tickets_by_status(),
            "total_users": User.objects.count(),
        }

    def is_admin(self, user):
        """Check if a user has admin privileges."""
        return user.is_superuser or user.is_staff

    def tickets_by_status(self):
        """Returns a count of tickets by status."""
        return Ticket.status_counts()

    def handle_scope(self, user, scope):
        """Handles the tickets to display depending on the scope selected by the user"""
        if not user.is_staff:
            return self.annotated_tickets(user, scope="personal"), "personal"

        if scope not in ("personal", "department", "assigned"):
            scope = "personal"

        return self.annotated_tickets(user, scope=scope), scope

    def base_tickets(self, user, scope="personal"):
        """Tickets visible to this user."""
        return Ticket.base_for_scope(user, scope=scope)

    def annotated_tickets(self, user, scope="personal"):
        """Annotate the base ticket queryset with message metadata."""
        return Ticket.annotated_for_home(user, scope=scope)

    def _annotate_last_message(self, qs, user):
        """Annotate the queryset with details of the last message and last read timestamp."""
        return Ticket._annotate_last_message_for_user(qs, user
                                                      )

    def _annotate_unread_count(self, qs, user):
        """Annotate the queryset with the count of unread messages for the user."""
        return Ticket._annotate_unread_count_for_user(qs, user)

    def completed_tickets(self, qs):
        """Tickets that are completed/closed."""
        return Ticket.completed_from(qs)

    def overdue_tickets(self, qs):
        """Tickets that are overdue for a response."""
        return Ticket.overdue_from(qs)

    def active_tickets(self, qs, overdue):
        """Tickets that are active and not overdue."""
        return Ticket.active_from(qs, overdue)
