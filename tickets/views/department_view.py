from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View

from tickets.forms import DepartmentFAQForm
from tickets.models import Department, DepartmentFAQ


class DepartmentView(LoginRequiredMixin, View):
    """View for displaying department details."""

    def get(self, request, department_slug):
        """Handle GET requests for the department view."""
        department = Department.get_by_slug_or_404(department_slug)
        if not department.can_view(request.user):
            return HttpResponseForbidden("You are not allowed to access this.")
        return render(request, "department.html", department.build_view_context(request))

    def post(self, request, department_slug):
        """Handle POST requests for staff and FAQ actions."""
        department = Department.get_by_slug_or_404(department_slug)
        if not department.can_manage_staff(request.user):
            return HttpResponseForbidden("You are not allowed to access this.")
        action = request.POST.get("action")
        if action in ("add_faq", "delete_faq"):
            if not department.can_manage_faqs(request.user):
                return HttpResponseForbidden("You are not allowed to access this.")
            if action == "add_faq":
                return self._handle_add_faq(request, department)
            return self._handle_delete_faq(request, department)
        self._process_staff_action(request, department)
        return redirect("department", department_slug=department_slug)

    def _handle_add_faq(self, request, department):
        """Handle FAQ creation POST."""
        form = DepartmentFAQForm(request.POST)
        if form.is_valid():
            faq = form.save(commit=False)
            faq.department = department
            faq.created_by = request.user
            faq.save()
            messages.success(request, "FAQ added successfully.")
        else:
            messages.error(request, "Please fill in both the question and answer fields.")
        return redirect("department", department_slug=department.slug)

    def _handle_delete_faq(self, request, department):
        """Handle FAQ deletion POST."""
        faq = get_object_or_404(DepartmentFAQ, id=request.POST.get("faq_id"), department=department)
        faq.delete()
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