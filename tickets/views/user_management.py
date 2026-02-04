from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect
from django.views import View
from django.views.generic import ListView

User = get_user_model()


class UserManagementView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    """View to list all users with pagination and search functionality."""

    model = User
    template_name = 'user_management.html'
    context_object_name = 'users'
    paginate_by = 10

    def test_func(self):
        """Check if user is staff or superuser."""
        return self.request.user.is_staff or self.request.user.is_superuser

    def get_queryset(self):
        """Return filtered and sorted user list."""
        queryset = User.objects.annotate(department_count=Count('user'))
        return self._filter_and_order(queryset)

    def _filter_and_order(self, queryset):
        """Helper to filter and order queryset."""
        search_query = self.request.GET.get('q')

        if search_query:
            queryset = queryset.filter(
                Q(username__icontains=search_query) |
                Q(first_name__icontains=search_query) |
                Q(last_name__icontains=search_query) |
                Q(email__icontains=search_query)
            )

        return queryset.order_by(
            '-is_superuser', '-is_staff', 'last_name', 'first_name'
        )

    def get_context_data(self, **kwargs):
        """Add search query to context."""
        context = super().get_context_data(**kwargs)
        context['search_query'] = self.request.GET.get('q', '')
        return context


class ToggleUserStatusView(LoginRequiredMixin, UserPassesTestMixin, View):
    """View to toggle user activation status."""

    def test_func(self):
        """Check if user is staff or superuser."""
        return self.request.user.is_staff or self.request.user.is_superuser

    def post(self, request, pk):
        """Toggle the active status of the user."""
        user_to_toggle = get_object_or_404(User, pk=pk)

        # Prevent deactivating yourself
        if user_to_toggle == request.user:
            return redirect('manage_users')

        # Prevent non supersusers from deactivating anyone
        if not request.user.is_superuser:
            return redirect('manage_users')

        user_to_toggle.is_active = not user_to_toggle.is_active
        user_to_toggle.save()
        return redirect('manage_users')
