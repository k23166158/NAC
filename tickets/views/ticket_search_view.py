from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView

from tickets.models import Ticket


class TicketSearchView(LoginRequiredMixin, ListView):
    """Display a searchable, filterable ticket index."""

    template_name = "ticket_search.html"
    context_object_name = "tickets"
    paginate_by = 10

    def get_queryset(self):
        """Return ticket queryset for the current search/filter request."""
        self.filters = Ticket.search_filters_from(self.request.GET)
        self.filters["scope"] = Ticket.normalize_scope_for(
            self.request.user,
            self.filters["scope"],
        )
        return Ticket.search_page_queryset(self.request.user, self.filters)

    def get_context_data(self, **kwargs):
        """Add filter state and option datasets to the page context."""
        context = super().get_context_data(**kwargs)
        context["filters"] = self.filters
        context["scope_options"] = Ticket.allowed_scopes_for(self.request.user)
        context.update(
            Ticket.search_filter_options(
                self.request.user,
                self.filters["scope"],
                self.filters["department"],
            )
        )
        context["pagination_query"] = self._pagination_query()
        return context

    def _pagination_query(self):
        """Return the querystring suffix used by pagination links."""
        data = self.request.GET.copy()
        data.pop("page", None)
        query = data.urlencode()
        return f"&{query}" if query else ""
