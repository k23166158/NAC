from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.shortcuts import redirect
from django.views.generic import ListView

from tickets.models import Department, DepartmentInvitation


class DepartmentManageView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    """View for managing departments. Only accessible to staff members."""

    template_name = "department_manage.html"
    context_object_name = "departments"
    paginate_by = 10
    login_url = "/login/"
    raise_exception = False

    def test_func(self):
        """Check if the user is a staff member."""
        return self.request.user.is_staff or self.request.user.is_superuser

    def get_queryset(self):
        """Return filtered, annotated departments for the current user."""
        return Department.assigned_to_user_with_ticket_counts(
            self.request.user,
            self.request.GET.get("q", ""),
        )

    def get_context_data(self, **kwargs):
        """Add invitation data to the rendered page context."""
        context = super().get_context_data(**kwargs)
        context["invitations"] = DepartmentInvitation.pending_for_user(self.request.user)
        return context

    def post(self, request):
        """Handle POST requests: accept or decline department invitations."""
        level, text = DepartmentInvitation.process_action_for_user(
            user=request.user,
            invite_id=request.POST.get("invite_id"),
            action=request.POST.get("action"),
        )
        getattr(messages, level)(request, text)
        return redirect("department_manage")
