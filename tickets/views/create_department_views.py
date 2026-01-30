from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.shortcuts import redirect
from django.views import View

from ..forms import CreateDepartmentForm
from ..models import UserDepartments


class CreateDepartmentView(LoginRequiredMixin, UserPassesTestMixin, View):
    """View for creating a new department. Only accessible to staff members."""
    login_url = '/login/'
    raise_exception = False

    def test_func(self):
        """Check if the user is a staff member."""
        return self.request.user.is_staff

    def get(self, request):
        """Handle GET requests - display the create department form."""
        form = CreateDepartmentForm()
        return self._render_form(request, form)

    def post(self, request):
        """Handle POST requests - process the create department form."""
        form = CreateDepartmentForm(request.POST)
        if form.is_valid():
            department = form.save(commit=False)
            department.created_by = request.user
            department.save()
            UserDepartments.objects.get_or_create(user=request.user, department=department)
            return redirect('department', department_slug=department.slug)
        return self._render_form(request, form)

    def _render_form(self, request, form):
        """Helper method to render the form template."""
        from django.shortcuts import render
        return render(request, 'create_department.html', {'form': form})

