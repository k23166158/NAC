from django.views.generic import ListView
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db.models import Count

User = get_user_model()

class UserManagementView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    model = User
    template_name = 'user_management.html'
    context_object_name = 'users'

    def test_func(self):
        return self.request.user.is_staff or self.request.user.is_superuser

    def get_queryset(self):
        return User.objects.annotate(department_count=Count('user')).order_by('last_name', 'first_name')
