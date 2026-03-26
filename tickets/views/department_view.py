from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponseForbidden
from django.shortcuts import redirect, render
from django.views import View

from tickets.forms import DepartmentFAQForm
from tickets.models import Department, DepartmentFAQ


class DepartmentView(LoginRequiredMixin, View):
    """View for displaying department details."""

    def get(self, request, department_slug):
        """Handle GET requests for the department view."""
        department = Department.get_by_slug_or_404(department_slug)
        if self._should_render_public_view(request.user, department):
            return render(request, "department_public.html", department.build_public_view_context(request))
        if not department.can_view(request.user):
            return HttpResponseForbidden("You are not allowed to access this.")
        return render(request, "department.html", department.build_view_context(request))

    def post(self, request, department_slug):
        """Handle POST requests for staff and FAQ actions."""
        department = Department.get_by_slug_or_404(department_slug)
        if self._should_render_public_view(request.user, department):
            return HttpResponseForbidden("You are not allowed to access this.")
        action = request.POST.get("action")
        if action in ("add_faq", "edit_faq", "delete_faq"):
            return self._dispatch_faq_action(request, department, action)
        if not department.can_manage_staff(request.user):
            return HttpResponseForbidden("You are not allowed to access this.")
        self._process_staff_action(request, department)
        return redirect("department", department_slug=department_slug)

    def _dispatch_faq_action(self, request, department, action):
        """Check FAQ permissions and route to the correct FAQ handler."""
        if not department.can_manage_faqs(request.user):
            return HttpResponseForbidden("You are not allowed to access this.")
        if action == "add_faq":
            return self._handle_add_faq(request, department)
        if action == "edit_faq":
            return self._handle_edit_faq(request, department)
        return self._handle_delete_faq(request, department)

    def _handle_add_faq(self, request, department):
        """Handle FAQ creation POST."""
        form = DepartmentFAQForm(request.POST)
        if form.is_valid():
            DepartmentFAQ.create_from_form(form, department=department, actor=request.user)
            messages.success(request, "FAQ added successfully.")
        else:
            messages.error(request, "Please fill in both the question and answer fields.")
        return redirect("department", department_slug=department.slug)

    def _handle_edit_faq(self, request, department):
        """Handle FAQ edit POST."""
        faq = DepartmentFAQ.get_for_department_or_404(
            faq_id=request.POST.get("faq_id"),
            department=department,
        )
        form = DepartmentFAQForm(request.POST, instance=faq)
        if form.is_valid():
            DepartmentFAQ.update_from_form(form)
            messages.success(request, "FAQ updated.")
        else:
            messages.error(request, "Please fill in both the question and answer fields.")
        return redirect("department", department_slug=department.slug)

    def _handle_delete_faq(self, request, department):
        """Handle FAQ deletion POST."""
        faq = DepartmentFAQ.get_for_department_or_404(
            faq_id=request.POST.get("faq_id"),
            department=department,
        )
        faq.delete_for_department(department)
        messages.success(request, "FAQ deleted.")
        return redirect("department", department_slug=department.slug)

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

    @staticmethod
    def _should_render_public_view(user, department):
        """Return True when the user should see the read-only department view."""
        if not user.is_authenticated or user.is_superuser:
            return False
        if not user.is_staff:
            return True
        return not department.can_view(user)

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
