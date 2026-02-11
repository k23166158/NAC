from django.shortcuts import render
from tickets.views import DepartmentFormView
from django.http import HttpResponseForbidden

class CreateDepartmentView(DepartmentFormView):
    """View for creating a new department. Only accessible to staff members."""
    
    def render_form(self, request, form):
        """Helper method to render the form template."""

        if not request.user.is_staff and not request.user.is_superuser:
            return HttpResponseForbidden("You are not allowed to create a department.")

        return render(request, 'department_form.html', {'form': form, 'type': 'create'})

