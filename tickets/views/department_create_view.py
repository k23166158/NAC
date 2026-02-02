from django.shortcuts import render
from tickets.views import DepartmentFormView

class CreateDepartmentView(DepartmentFormView):
    """View for creating a new department. Only accessible to staff members."""
    
    def render_form(self, request, form):
        """Helper method to render the form template."""
        return render(request, 'department_form.html', {'form': form, 'type': 'create'})

