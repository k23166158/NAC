from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.shortcuts import redirect
from django.views import View
from django.views.generic import ListView

from tickets.models import User


class UserManagementView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    """View to list all users with pagination and search functionality."""

    model = User
    template_name = 'user_management.html'
    context_object_name = 'users'
    paginate_by = 10

    def test_func(self):
        """Check if user is staff or superuser."""
        return self.request.user.has_management_access()

    def get_queryset(self):
        """Return filtered and sorted user list."""
        search_query = self.request.GET.get("q", "")
        return User.managed_queryset(search_query)

    def get_context_data(self, **kwargs):
        """Add search query to context."""
        context = super().get_context_data(**kwargs)
        context['search_query'] = self.request.GET.get('q', '')
        return context


class ToggleUserStatusView(LoginRequiredMixin, UserPassesTestMixin, View):
    """View to toggle user activation status."""

    def test_func(self):
        """Check if user is staff or superuser."""
        return self.request.user.has_management_access()

    def post(self, request, pk):
        """Toggle the active status of the user."""
        user_to_toggle = User.get_by_pk_or_404(pk)
        request.user.toggle_user_active(user_to_toggle)
        return redirect("manage_users")
