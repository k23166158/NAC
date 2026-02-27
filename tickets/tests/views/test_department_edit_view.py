from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from tickets.models import Department
from tickets.views.department_form_view import DepartmentFormView

User = get_user_model()

class EditDepartmentViewTests(TestCase):
    """Tests to achieve 100% coverage for EditDepartmentView and base form view."""

    def setUp(self):
        """Set up test client and users."""
        self.client = Client()
        self.staff_user = User.objects.create_user(
            username="staff", email="staff@example.com", password="pw", is_staff=True
        )
        self.department = Department.objects.create(
            name="Edit Dept", 
            slug="edit-dept", 
            created_by=self.staff_user
        )
        self.url = reverse('edit_department', kwargs={'department_slug': self.department.slug})

    def test_get_edit_form_success(self):
        """Test GET request renders form with existing data."""
        self.client.force_login(self.staff_user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'department_form.html')
        self.assertEqual(response.context['type'], 'edit')

    def test_post_edit_success(self):
        """Test POST request updates existing department."""
        self.client.force_login(self.staff_user)
        data = {'name': 'Updated Name', 'description': 'Updated Description'}
        response = self.client.post(self.url, data)
        
        self.department.refresh_from_db()
        self.assertEqual(self.department.name, 'Updated Name')
        self.assertEqual(response.status_code, 302)

    def test_edit_permission_denied(self):
        """Test that non-creators/non-superusers are denied access."""
        other_user = User.objects.create_user(username="other", password="pw", is_staff=True)
        self.client.force_login(other_user)
        
        # Test GET
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 403)
        
        # Test POST
        response = self.client.post(self.url, {'name': 'Hack'})
        self.assertEqual(response.status_code, 403)

    def test_base_form_view_not_implemented(self):
        """Test that the base DepartmentFormView raises NotImplementedError."""
        view = DepartmentFormView()
        with self.assertRaises(NotImplementedError):
            view.render_form(None, None)