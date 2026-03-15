from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponseForbidden
from django.shortcuts import redirect, render
from django.views import View

from tickets.models import Department


class DepartmentView(LoginRequiredMixin, View):
    """View for displaying department details."""

    def get(self, request, department_slug):
        """Handle GET requests for the department view."""
        department = Department.get_by_slug_or_404(department_slug)
        if not department.can_view(request.user):
            return HttpResponseForbidden("You are not allowed to access this.")
        return render(request, "department.html", department.build_view_context(request))

    def post(self, request, department_slug):
        """Handle POST requests to add or remove staff."""
        department = Department.get_by_slug_or_404(department_slug)
        if not department.can_manage_staff(request.user):
            return HttpResponseForbidden("You are not allowed to access this.")
        self._process_staff_action(request, department)
        return redirect("department", department_slug=department_slug)

    def _process_staff_action(self, request, department):
        """Run department staff action and publish any response message."""
        outcome = department.process_staff_change(
            actor=request.user,
            user_id=request.POST.get("user_id"),
            action=request.POST.get("action"),
        )
        if not outcome:
            return
        level, text = outcome
        getattr(messages, level)(request, text)

    def update_staff_assignment(self, request, user_id, department, action):
        """Update staff assignment for a user in a department.
        
        This is a no-op for unknown actions.
        """
        outcome = department.process_staff_change(
            actor=request.user,
            user_id=user_id,
            action=action,
        )
        if not outcome:
            return
        level, text = outcome
        getattr(messages, level)(request, text)