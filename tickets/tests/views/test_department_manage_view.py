from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from tickets.models import Department, UserDepartments

User = get_user_model()


class DepartmentManageViewTests(TestCase):
    """Tests for the DepartmentManageView."""

    def _create_user(self, username, email, first_name, last_name, is_staff):
        """Helper method to create a user."""
        return User.objects.create_user(
            username=username, email=email, password="password123",
            first_name=first_name, last_name=last_name, is_staff=is_staff
        )

    def setUp(self):
        """Set up test client and users."""
        self.client = Client()
        self.url = reverse('department_manage')
        self.staff_user = self._create_user("staffuser", "staff@example.com", "Staff", "User", True)
        self.regular_user = self._create_user("regularuser", "regular@example.com", "Regular", "User", False)
        self.other_staff = self._create_user("otherstaff", "other@example.com", "Other", "Staff", True)

    def test_get_request_anonymous_user(self):
        """Test that anonymous users are redirected to login."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login/', response.url)

    def test_get_request_non_staff_user(self):
        """Test that non-staff users are denied access when accessing the view."""
        self.client.force_login(self.regular_user)
        response = self.client.get(self.url)
        # UserPassesTestMixin returns 403 Forbidden for non-staff users
        self.assertEqual(response.status_code, 403)

    def test_get_request_staff_user_no_departments(self):
        """Test that staff users see empty list when they have no departments."""
        self.client.force_login(self.staff_user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'department_manage.html')
        self.assertIn('departments', response.context)
        self.assertEqual(list(response.context['departments']), [])

    def test_get_request_staff_user_with_departments(self):
        """Test that staff users see only departments they are assigned to."""
        dept1 = Department.objects.create(name="IT Support", created_by=self.staff_user)
        dept2 = Department.objects.create(name="Finance", created_by=self.staff_user)
        dept3 = Department.objects.create(name="HR", created_by=self.other_staff)

        # Assign staff_user to dept1 and dept2
        UserDepartments.objects.create(user=self.staff_user, department=dept1)
        UserDepartments.objects.create(user=self.staff_user, department=dept2)
        # Assign other_staff to dept3
        UserDepartments.objects.create(user=self.other_staff, department=dept3)

        self.client.force_login(self.staff_user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'department_manage.html')
        self.assertIn('departments', response.context)
        
        departments = list(response.context['departments'])
        self.assertEqual(len(departments), 2)
        # Should be ordered by name
        self.assertEqual(departments[0].name, "Finance")
        self.assertEqual(departments[1].name, "IT Support")

    def test_get_request_staff_user_departments_ordered_by_name(self):
        """Test that departments are ordered by name."""
        dept1 = Department.objects.create(name="Zebra Department", created_by=self.staff_user)
        dept2 = Department.objects.create(name="Alpha Department", created_by=self.staff_user)
        dept3 = Department.objects.create(name="Beta Department", created_by=self.staff_user)

        UserDepartments.objects.create(user=self.staff_user, department=dept1)
        UserDepartments.objects.create(user=self.staff_user, department=dept2)
        UserDepartments.objects.create(user=self.staff_user, department=dept3)

        self.client.force_login(self.staff_user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        
        departments = list(response.context['departments'])
        self.assertEqual(len(departments), 3)
        self.assertEqual(departments[0].name, "Alpha Department")
        self.assertEqual(departments[1].name, "Beta Department")
        self.assertEqual(departments[2].name, "Zebra Department")

    def test_get_request_staff_user_excludes_unassigned_departments(self):
        """Test that staff users don't see departments they're not assigned to."""
        dept1 = Department.objects.create(name="Assigned Dept", created_by=self.staff_user)
        dept2 = Department.objects.create(name="Unassigned Dept", created_by=self.staff_user)

        # Only assign dept1
        UserDepartments.objects.create(user=self.staff_user, department=dept1)

        self.client.force_login(self.staff_user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        
        departments = list(response.context['departments'])
        self.assertEqual(len(departments), 1)
        self.assertEqual(departments[0].name, "Assigned Dept")

    def test_test_func_returns_true_for_staff(self):
        """Test that test_func returns True for staff users."""
        from tickets.views.department_manage_view import DepartmentManageView
        view = DepartmentManageView()
        view.request = type('Request', (), {'user': self.staff_user})()
        self.assertTrue(view.test_func())

    def test_test_func_returns_false_for_non_staff(self):
        """Test that test_func returns False for non-staff users."""
        from tickets.views.department_manage_view import DepartmentManageView
        view = DepartmentManageView()
        view.request = type('Request', (), {'user': self.regular_user})()
        self.assertFalse(view.test_func())

