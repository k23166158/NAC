from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.http import HttpResponseForbidden
from django.shortcuts import redirect, render
from django.views import View

from tickets.models import Department

class DeleteDepartmentView(LoginRequiredMixin, UserPassesTestMixin, View):
    """View for deleting a department. Only accessible to staff members who created it."""
    login_url = '/login/'
    raise_exception = False

    def test_func(self):
        """Check if the user is a staff member."""
        return self.request.user.is_staff or self.request.user.is_superuser

    def get(self, request, department_slug):
        """Handle GET requests - display the confirmation warning."""
        department = Department.get_by_slug_or_404(department_slug)
        if not department.can_delete(request.user):
            return HttpResponseForbidden("You are not allowed to delete this department.")

        return render(request, 'department_delete.html', {'department': department})

    def post(self, request, department_slug):
        """Handle POST requests - perform the deletion."""
        department = Department.get_by_slug_or_404(department_slug)
        if not department.can_delete(request.user):
            return HttpResponseForbidden("You are not allowed to delete this department.")

        department.delete_for_actor(request.user)
        return redirect('home')
