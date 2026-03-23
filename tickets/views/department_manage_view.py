from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponseForbidden
from django.shortcuts import redirect
from django.views.generic import ListView

from tickets.models import Department, DepartmentInvitation


class DepartmentManageView(LoginRequiredMixin, ListView):
    """View for managing or browsing departments."""

    template_name = "department_manage.html"
    context_object_name = "departments"
    paginate_by = 9
    login_url = "/login/"

    def get_queryset(self):
        """Return filtered, annotated departments for the current user."""
        if self._can_manage_departments():
            return Department.assigned_to_user_with_ticket_counts(
                self.request.user,
                self.request.GET.get("q", ""),
            )
        return Department.browsable_with_active_member_counts(
            self.request.GET.get("q", "")
        )

    def get_context_data(self, **kwargs):
        """Add invitation data to the rendered page context."""
        context = super().get_context_data(**kwargs)
        context.update(self._page_context())
        return context

    def post(self, request):
        """Handle POST requests: accept or decline department invitations."""
        if not self._can_manage_departments():
            return HttpResponseForbidden("You are not allowed to access this.")
        level, text = DepartmentInvitation.process_action_for_user(
            user=request.user,
            invite_id=request.POST.get("invite_id"),
            action=request.POST.get("action"),
        )
        getattr(messages, level)(request, text)
        return redirect("department_manage")

    def _page_context(self):
        """Return role-specific page context."""
        if self._can_manage_departments():
            return {
                "browse_only": False,
                "page_title": "Manage Departments",
                "page_departments_label": "Your Departments",
                "invitations": DepartmentInvitation.pending_for_user(self.request.user),
            }
        return {
            "browse_only": True,
            "page_title": "Departments",
            "page_departments_label": "All Departments",
            "invitations": [],
        }

    def _can_manage_departments(self):
        """Return whether the current user may manage departments."""
        return self.request.user.is_staff or self.request.user.is_superuser
