from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.shortcuts import render


class DepartmentManageView(LoginRequiredMixin, UserPassesTestMixin, View):
    """View for managing departments. Only accessible to staff members."""
    login_url = '/login/'
    raise_exception = False

    def test_func(self):
        """Check if the user is a staff member."""
        return self.request.user.is_staff

    def get(self, request):
        """Handle GET requests for the department manage view."""
        return render(request, "department_manage.html")

