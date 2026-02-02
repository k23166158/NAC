from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render


class DepartmentManageView(LoginRequiredMixin, View):
    """View for managing departments."""

    def get(self, request):
        """Handle GET requests for the department manage view."""
        return render(request, "department_manage.html")

