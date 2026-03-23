from django.http import HttpResponseForbidden
from django.shortcuts import render

from tickets.models import Department
from tickets.views import DepartmentFormView

class EditDepartmentView(DepartmentFormView):
    """View for editing an existing department. Only accessible to staff members."""

    def get(self, request, department_slug):
        """Handle GET requests - display the department form with existing data."""
        department = Department.get_by_slug_or_404(department_slug)
        if not department.can_edit(request.user):
            return HttpResponseForbidden("You are not allowed to edit this department.")
        
        return super().get(request, instance=department)
    
    def post(self, request, department_slug):
        """Handle POST requests - process the department form with existing data."""
        department = Department.get_by_slug_or_404(department_slug)
        if not department.can_edit(request.user):
            return HttpResponseForbidden("You are not allowed to edit this department.")

        return super().post(request, instance=department)

    def render_form(self, request, form):
        """Helper method to render the form template."""
        return render(request, 'department_form.html', {'form': form, 'type': 'edit', 'department': form.instance})
