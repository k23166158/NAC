from django.shortcuts import render, get_object_or_404
from tickets.views import DepartmentFormView
from tickets.models import Department

class EditDepartmentView(DepartmentFormView):
    """View for editing an existing department. Only accessible to staff members."""

    def get(self, request, department_slug):
        """Handle GET requests - display the department form with existing data."""
        department = get_object_or_404(Department, slug=department_slug)
        return super().get(request, instance=department)
    
    def post(self, request, department_slug):
        """Handle POST requests - process the department form with existing data."""
        department = get_object_or_404(Department, slug=department_slug)
        return super().post(request, instance=department)

    def render_form(self, request, form):
        """Helper method to render the form template."""
        return render(request, 'department_form.html', {'form': form, 'type': 'edit', 'department': form.instance})