from django.views.generic import ListView
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect
from django.views import View

User = get_user_model()

class UserManagementView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    model = User
    template_name = 'user_management.html'
    context_object_name = 'users'

    def test_func(self):
        return self.request.user.is_staff or self.request.user.is_superuser

    def get_queryset(self):
        return User.objects.annotate(department_count=Count('user')).order_by('last_name', 'first_name')

class ToggleUserStatusView(LoginRequiredMixin, UserPassesTestMixin, View):
    def test_func(self):
        return self.request.user.is_staff or self.request.user.is_superuser

    def post(self, request, pk):
        user_to_toggle = get_object_or_404(User, pk=pk)

        # Prevent deactivating yourself
        if user_to_toggle == request.user:
            return redirect('manage_users')

        # Prevent staff from deactivating superusers
        if user_to_toggle.is_superuser and not request.user.is_superuser:
            return redirect('manage_users')

        user_to_toggle.is_active = not user_to_toggle.is_active
        user_to_toggle.save()
        return redirect('manage_users')
