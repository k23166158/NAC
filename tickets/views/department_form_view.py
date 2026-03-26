from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.shortcuts import redirect
from django.views import View

from tickets.forms import DepartmentForm

class DepartmentFormView(LoginRequiredMixin, UserPassesTestMixin, View):
    """View for displaying a department form. Only accessible to staff members."""
    login_url = '/login/'
    raise_exception = False

    def test_func(self):
        """Check if the user is a staff member."""
        return self.request.user.is_staff or self.request.user.is_superuser

    def get(self, request, instance=None):
        """Handle GET requests - display the department form."""
        form = DepartmentForm(instance=instance)
        return self.render_form(request, form)

    def post(self, request, instance=None):
        """Handle POST requests - process the department form."""
        form = DepartmentForm(request.POST, instance=instance)
        if form.is_valid():
            department = form.save_for_actor(request.user)
            return redirect('department', department_slug=department.slug)
        return self.render_form(request, form)

    def render_form(self, request, form):
        """Helper method to render the form template."""
        raise NotImplementedError("Subclasses must implement render_form method.")
    
