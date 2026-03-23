from django.shortcuts import render
from django.views import View

from tickets.models import Ticket, User


class HomeView(View):
    """View for the home page/dashboard."""

    def get(self, request):
        """Handle GET request for home page."""
        if not request.user.is_authenticated:
            return render(request, "unauthenticated_home.html")

        qs, scope = self.filtered_ticket_state(request)
        ctx = self.get_context(request, qs, scope)
        ctx.update(self.get_search_context(request.user, scope))
        if self.is_admin(request.user):
            ctx.update(self.get_admin_stats())

        return render(request, "home_view.html", ctx)

    def _get_page(self, request, queryset, param_name, per_page=10):
        """Helper method to return a paginated page."""
        from django.core.paginator import Paginator
        return Paginator(queryset, per_page).get_page(request.GET.get(param_name, 1))

    def get_context(self, request, qs, scope):
        """Build the base context dictionary for the view, with pagination for the lists."""
        active_qs = self.active_tickets(qs)
        completed_qs = self.completed_tickets(qs)
        context = self.base_context(active_qs, completed_qs, scope)
        context["display_visible_ticket_count"] = self.display_visible_ticket_count(
            request,
            context["visible_ticket_count"],
        )
        context["active_tickets_page"] = self._get_page(request, active_qs, 'active_page')
        context["completed_tickets_page"] = self._get_page(request, completed_qs, 'completed_page')
        context["active_pagination_query"] = self._pagination_query(request, "active_page")
        context["completed_pagination_query"] = self._pagination_query(request, "completed_page")
        return context

    def filtered_ticket_state(self, request):
        """Return the filtered home-query ticket state for the current request."""
        self.filters = Ticket.search_filters_from(request.GET)
        self.applied_filters = self.applied_filters_for(request, self.filters)
        scope = self.filters["scope"]
        qs, scope = self.handle_scope(request.user, scope)
        self.filters["scope"] = scope
        self.applied_filters["scope"] = scope
        qs = self.apply_filters(qs, self.applied_filters)
        return qs, scope

    @staticmethod
    def base_context(active_qs, completed_qs, scope):
        """Return the non-paginated home context values."""
        return {
            "scope": scope,
            "completed_tickets": completed_qs,
            "active_tickets": active_qs,
            "visible_ticket_count": active_qs.count() + completed_qs.count(),
        }

    def _pagination_query(self, request, page_param):
        """Return a querystring suffix preserving all filters except one page param."""
        data = request.GET.copy()
        data.pop(page_param, None)
        query = data.urlencode()
        return f"&{query}" if query else ""

    def get_search_context(self, user, scope):
        """Return context required for the integrated ticket search form."""
        department_id = self.filters.get("department", "")
        staff_id = self.filters.get("assigned_staff", "")
        return {
            "filters": self.filters,
            "applied_filters": self.applied_filters,
            "scope_options": Ticket.allowed_scopes_for(user),
            **Ticket.search_filter_options(user, scope, department_id, staff_id),
        }

    @staticmethod
    def display_visible_ticket_count(request, actual_count):
        """Return the count label value to show after dependent auto-refreshes."""
        if request.GET.get("auto_refresh") != "dependent":
            return actual_count
        display_count = request.GET.get("display_count", "")
        return int(display_count) if display_count.isdigit() else actual_count

    @staticmethod
    def applied_filters_for(request, current_filters):
        """Return the filters currently applied to the queue results."""
        if request.GET.get("auto_refresh") != "dependent":
            return current_filters.copy()
        return {
            key: request.GET.get(f"applied_{key}", current_filters[key])
            for key in current_filters
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

    def apply_filters(self, qs, filters):
        """Apply ticket search filters to the annotated home queryset."""
        return Ticket._apply_search_filters(qs, filters).distinct()

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

    def active_tickets(self, qs):
        """Tickets that are active."""
        return Ticket.active_from(qs)
