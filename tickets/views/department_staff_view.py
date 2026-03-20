from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.paginator import Paginator
from django.http import HttpResponseForbidden
from django.shortcuts import render
from django.views import View

from tickets.models import Department


class DepartmentStaffView(LoginRequiredMixin, View):
    """List all staff members for a department with pagination."""

    def get(self, request, department_slug):
        """Handle GET request for staff members list."""
        department = Department.get_by_slug_or_404(department_slug)
        if not department.can_view(request.user):
            return HttpResponseForbidden("You are not allowed to access this.")

        current_staff = department.get_current_staff()
        invited_users = [i.recipient for i in department.get_pending_invitations()]
        paginator = Paginator(current_staff + invited_users, 8)
        page = paginator.get_page(request.GET.get("page"))

        return render(request, "department_staff.html", {
            "department": department,
            "page": page,
            "invited_users": invited_users,
        })
