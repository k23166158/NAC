from django.http import HttpResponseForbidden
from django.shortcuts import redirect, render
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views import View

from tickets.models import Department


class DepartmentView(LoginRequiredMixin, View):
    """View for displaying department details."""

    def get(self, request, department_slug):
        """Handle GET requests for the department view."""
        department = Department.get_by_slug_or_404(department_slug)

        if not department.can_view(request.user):
            return HttpResponseForbidden("You are not allowed to access this.")

        context = department.build_view_context()
        return render(request, "department.html", context)

    def post(self, request, department_slug):
        """Handle POST requests to add or remove staff."""
        department = Department.get_by_slug_or_404(department_slug)

        if not department.can_manage_staff(request.user):
            return HttpResponseForbidden("You are not allowed to access this.")

        outcome = department.process_staff_change(
            actor=request.user,
            user_id=request.POST.get("user_id"),
            action=request.POST.get("action"),
        )
        if outcome:
            level, text = outcome
            getattr(messages, level)(request, text)

        return redirect("department", department_slug=department_slug)
