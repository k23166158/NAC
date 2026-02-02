from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from tickets.models import Department

User = get_user_model()

class DeleteDepartmentViewTests(TestCase):
    """Tests to achieve 100% coverage for DeleteDepartmentView."""

    def setUp(self):
        """Set up test client and users."""
        self.client = Client()
        self.owner = User.objects.create_user(
            username="owner", email="owner@example.com", password="pw", is_staff=True
        )
        self.other_staff = User.objects.create_user(
            username="otherstaff", email="other@example.com", password="pw", is_staff=True
        )
        self.department = Department.objects.create(
            name="Delete Dept", 
            slug="delete-dept", 
            created_by=self.owner
        )
        self.url = reverse('delete_department', kwargs={'department_slug': self.department.slug})

    def test_get_confirm_delete_success(self):
        """Test GET request displays confirmation by owner."""
        self.client.force_login(self.owner)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'department_delete.html')

    def test_post_delete_success(self):
        """Test POST request deletes department by owner."""
        self.client.force_login(self.owner)
        response = self.client.post(self.url)
        self.assertRedirects(response, reverse('home'))
        self.assertFalse(Department.objects.filter(id=self.department.id).exists())

    def test_forbidden_for_non_owner_staff(self):
        """Test that non-owner staff are forbidden from GET and POST."""
        self.client.force_login(self.other_staff)
        
        # Test GET
        response_get = self.client.get(self.url)
        self.assertEqual(response_get.status_code, 403)
        
        # Test POST
        response_post = self.client.post(self.url)
        self.assertEqual(response_post.status_code, 403)