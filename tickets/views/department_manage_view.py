from django.shortcuts import redirect, render
from django.views import View
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin

from tickets.models import Department, DepartmentInvitation


class DepartmentManageView(LoginRequiredMixin, UserPassesTestMixin, View):
    """View for managing departments. Only accessible to staff members."""

    login_url = "/login/"
    raise_exception = False

    def test_func(self):
        """Check if the user is a staff member."""
        return self.request.user.is_staff or self.request.user.is_superuser

    def get(self, request):
        """Handle GET requests for the department manage view."""
        context = {
            "departments": Department.assigned_to_user_with_ticket_counts(request.user),
            "invitations": DepartmentInvitation.pending_for_user(request.user),
        }
        return render(request, "department_manage.html", context)

    def post(self, request):
        """Handle POST requests: accept or decline department invitations."""
        level, text = DepartmentInvitation.process_action_for_user(
            user=request.user,
            invite_id=request.POST.get("invite_id"),
            action=request.POST.get("action"),
        )
        getattr(messages, level)(request, text)
        return redirect("department_manage")
