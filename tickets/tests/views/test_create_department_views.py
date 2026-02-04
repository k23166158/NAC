from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from unittest.mock import patch

from tickets.models import Department, UserDepartments
from tickets.views import CreateDepartmentView
from tickets.forms import DepartmentForm

User = get_user_model()


class CreateDepartmentViewTests(TestCase):
    """Tests for the CreateDepartmentView."""

    def setUp(self):
        """Set up test client and users."""
        self.client = Client()
        self.url = reverse('create_department')

        self.staff_user = User.objects.create_user(
            username="staffuser",
            email="staff@example.com",
            password="password123",
            first_name="Staff",
            last_name="User",
            is_staff=True,
        )

        self.regular_user = User.objects.create_user(
            username="regularuser",
            email="regular@example.com",
            password="password123",
            first_name="Regular",
            last_name="User",
            is_staff=False,
        )

    def test_get_request_staff_user(self):
        """Test that staff users can access the create department form."""
        self.client.force_login(self.staff_user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'department_form.html')
        self.assertIsInstance(response.context['form'], DepartmentForm)

    def test_get_request_non_staff_user(self):
        """Test that non-staff users are denied access when accessing the form."""
        self.client.force_login(self.regular_user)
        response = self.client.get(self.url)
        # UserPassesTestMixin returns 403 Forbidden for non-staff users
        self.assertEqual(response.status_code, 403)

    def test_get_request_anonymous_user(self):
        """Test that anonymous users are redirected to login."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login/', response.url)

    def test_post_request_valid_form_staff_user(self):
        """Test successful department creation with valid form data."""
        self.client.force_login(self.staff_user)
        form_data = {
            'name': 'IT Support',
            'description': 'Information Technology Support'
        }
    
        response = self.client.post(self.url, data=form_data)

        self.assertTrue(Department.objects.filter(name='IT Support').exists())
        department = Department.objects.get(name='IT Support')
        self.assertEqual(department.created_by, self.staff_user)
        self.assertEqual(department.description, 'Information Technology Support')

        self.assertEqual(response.status_code, 302)

    def test_post_request_invalid_form_staff_user(self):
        """Test that invalid form data re-renders the form with errors."""
        self.client.force_login(self.staff_user)
        Department.objects.create(
            name='IT Support',
            created_by=self.staff_user
        )

        form_data = {
            'name': 'IT Support',
            'description': 'Duplicate'
        }
        response = self.client.post(self.url, data=form_data)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'department_form.html')
        self.assertFalse(response.context['form'].is_valid())
        self.assertIn('name', response.context['form'].errors)

    def test_post_request_non_staff_user(self):
        """Test that non-staff users cannot POST to create department."""
        self.client.force_login(self.regular_user)
        form_data = {
            'name': 'Test Department',
            'description': 'Test'
        }
        response = self.client.post(self.url, data=form_data)
        # UserPassesTestMixin returns 403 Forbidden for non-staff users
        self.assertEqual(response.status_code, 403)
        self.assertFalse(Department.objects.filter(name='Test Department').exists())

    def test_post_request_anonymous_user(self):
        """Test that anonymous users are redirected to login on POST."""
        form_data = {
            'name': 'Test Department',
            'description': 'Test'
        }
        response = self.client.post(self.url, data=form_data)
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login/', response.url)

    def test_test_func_returns_true_for_staff(self):
        """Test that test_func returns True for staff users."""
        view = CreateDepartmentView()
        view.request = type('Request', (), {'user': self.staff_user})()
        self.assertTrue(view.test_func())

    def test_test_func_returns_false_for_non_staff(self):
        """Test that test_func returns False for non-staff users."""
        
        view = CreateDepartmentView()
        view.request = type('Request', (), {'user': self.regular_user})()
        self.assertFalse(view.test_func())

    def test_render_form_helper_method(self):
        """Test that _render_form helper method renders correctly."""
        # Test _render_form by calling GET which uses it
        self.client.force_login(self.staff_user)
        response = self.client.get(self.url)
        # This tests _render_form indirectly through the GET method
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'department_form.html')
        self.assertIsInstance(response.context['form'], DepartmentForm)

    def test_department_created_by_is_set_correctly(self):
        """Test that department.created_by is set to the request user."""
        self.client.force_login(self.staff_user)
        form_data = {
            'name': 'HR Department',
            'description': 'Human Resources'
        }
            
        self.client.post(self.url, data=form_data)
        
        department = Department.objects.get(name='HR Department')
        self.assertEqual(department.created_by, self.staff_user)

    def test_creator_automatically_added_to_user_departments(self):
        """Test that department creator is automatically added to UserDepartments."""
        self.client.force_login(self.staff_user)
        form_data = {'name': 'Finance Department', 'description': 'Finance and Accounting'}

        self.client.post(self.url, data=form_data)
        
        department = Department.objects.get(name='Finance Department')
        user_department = UserDepartments.objects.get(
            user=self.staff_user, department=department
        )
        self.assertEqual(user_department.user, self.staff_user)
        self.assertEqual(user_department.department, department)

