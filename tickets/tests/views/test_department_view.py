from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from tickets.models import Department, UserDepartments

User = get_user_model()

class DepartmentViewTests(TestCase):
    """Tests for the DepartmentView."""

    def setUp(self):
        """Set up users and a department for testing."""
        self.client = Client()
        self.owner = User.objects.create_user(
            username="owner", email="owner@example.com", password="pw", is_staff=True
        )
        self.member = User.objects.create_user(
            username="member", email="member@example.com", password="pw"
        )
        self.outsider = User.objects.create_user(
            username="outsider", email="outsider@example.com", password="pw"
        )

        self.department = Department.objects.create(name="IT", created_by=self.owner)
        
        UserDepartments.objects.create(user=self.member, department=self.department)
        UserDepartments.objects.create(user=self.owner, department=self.department)

        self.url = reverse('department', kwargs={'department_slug': self.department.slug})

    def test_get_forbidden_for_non_member(self):
        """Test that non-members cannot access the department view."""
        self.client.force_login(self.outsider)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 403)

    def test_get_success_for_member(self):
        """Test that members can access the department view."""
        self.client.force_login(self.member)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "department.html")
        self.assertIn("active_tickets", response.context)
        self.assertIn("available_staff", response.context)

    def test_post_add_staff_success(self):
        """Test that the owner can add staff."""
        new_staff = User.objects.create_user(
            username="newstaff", email="newstaff@example.com", password="pw", is_staff=True
        )
        self.client.force_login(self.owner)
        
        response = self.client.post(
            self.url, 
            {'action': 'add', 'user_id': new_staff.id}
        )
        
        self.assertRedirects(response, self.url)
        self.assertTrue(
            UserDepartments.objects.filter(user=new_staff, department=self.department).exists()
        )

    def test_post_remove_staff_success(self):
        """Test that the owner can remove staff."""
        UserDepartments.objects.create(user=self.outsider, department=self.department)
        
        self.client.force_login(self.owner)
        response = self.client.post(
            self.url, 
            {'action': 'remove', 'user_id': self.outsider.id}
        )
        
        self.assertRedirects(response, self.url)
        self.assertFalse(
            UserDepartments.objects.filter(user=self.outsider, department=self.department).exists()
        )

    def test_post_forbidden_for_non_owner(self):
        """Test that regular members cannot add/remove staff."""
        self.client.force_login(self.member)
        response = self.client.post(
            self.url, 
            {'action': 'add', 'user_id': self.outsider.id}
        )
        self.assertEqual(response.status_code, 403)

    def test_post_no_user_id_does_nothing(self):
        """Test that submitting without a user_id safely redirects."""
        self.client.force_login(self.owner)
        response = self.client.post(self.url, {'action': 'add'})
        self.assertRedirects(response, self.url)

    def test_post_staff_non_owner_forbidden(self):
        """Test that staff who didn't create department cannot manage."""
        staff_user = User.objects.create_user(
            username="staff_other", email="so@example.com", password="pw", is_staff=True
        )
        self.client.force_login(staff_user)
        response = self.client.post(
            self.url,
            {'action': 'add', 'user_id': self.outsider.id}
        )
        self.assertEqual(response.status_code, 403)

    def test_post_unknown_action_ignored(self):
        """Test that an unknown action does not change staff."""
        self.client.force_login(self.owner)
        response = self.client.post(
            self.url,
            {'action': 'unknown', 'user_id': self.outsider.id}
        )
        self.assertRedirects(response, self.url)
        self.assertFalse(
            UserDepartments.objects.filter(
                user=self.outsider, department=self.department
            ).exists()
        )