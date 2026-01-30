from django.views import View

class DepartmentView(View):
    """View for displaying department details."""

    def get(self, request, department_id):
        """Handle GET requests for the department view."""
        pass