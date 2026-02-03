from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from tickets.models import UserDepartments, Department

User = get_user_model()


class UserManagementViewTest(TestCase):
    """Test suite for the user management view."""

    def setUp(self):
        """Set up test users and department."""
        self.superuser = User.objects.create_superuser(
            username='superuser', email='super@example.com', password='password123',
            first_name='Super', last_name='User'
        )
        self.staff_user = User.objects.create_user(
            username='staff', email='staff@example.com', password='password123',
            first_name='Staff', last_name='Member', is_staff=True
        )
        self.regular_user = User.objects.create_user(
            username='regular', email='regular@example.com', password='password123',
            first_name='Regular', last_name='User'
        )
        self.other_user = User.objects.create_user(
            username='other', email='other@example.com', password='password123',
            first_name='Other', last_name='Person'
        )
        self.department = Department.objects.create(
            name='IT', description='IT Department', created_by=self.superuser
        )
        UserDepartments.objects.create(user=self.staff_user, department=self.department)
        self.url = reverse('manage_users')

    def test_redirect_if_not_logged_in(self):
        """Ensure unauthenticated users are redirected to login."""
        response = self.client.get(self.url)
        self.assertRedirects(response, f'/login/?next={self.url}')

    def test_forbidden_for_regular_user(self):
        """Ensure regular users cannot access the view."""
        self.client.login(username='regular', password='password123')
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 403)

    def test_access_for_staff_user(self):
        """Ensure staff users can access the view and see correct data."""
        self.client.login(username='staff', password='password123')
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'user_management.html')
        self.assertIn('users', response.context)

        users = list(response.context['users'])
        staff = next(u for u in users if u.username == 'staff')
        self.assertEqual(staff.department_count, 1)

        regular = next(u for u in users if u.username == 'regular')
        self.assertEqual(regular.department_count, 0)

    def test_access_for_superuser(self):
        """Ensure superusers can access the view."""
        self.client.login(username='superuser', password='password123')
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_search_functionality(self):
        """Test user filtering by username and name."""
        self.client.login(username='superuser', password='password123')

        response = self.client.get(self.url, {'q': 'regular'})
        self.assertContains(response, 'regular')
        self.assertNotContains(response, 'staff')

        response = self.client.get(self.url, {'q': 'Other'})
        self.assertContains(response, 'Other')
        self.assertNotContains(response, 'Staff')

    def test_ordering(self):
        """Test default ordering of users."""
        self.client.login(username='superuser', password='password123')
        response = self.client.get(self.url)
        users = response.context['users']

        self.assertEqual(users[0], self.superuser)
        self.assertEqual(users[1], self.staff_user)
        self.assertEqual(users[2], self.other_user)
        self.assertEqual(users[3], self.regular_user)


class ToggleUserStatusViewTest(TestCase):
    """Test suite for toggling user status."""

    def setUp(self):
        """Set up test users."""
        self.superuser = User.objects.create_superuser(
            username='superuser', email='super@example.com', password='password123'
        )
        self.staff_user = User.objects.create_user(
            username='staff', email='staff@example.com', password='password123',
            is_staff=True
        )
        self.target_user = User.objects.create_user(
            username='target', email='target@example.com', password='password123',
            is_active=True
        )

    def test_toggle_deactivate(self):
        """Test deactivating an active user."""
        self.client.login(username='superuser', password='password123')
        url = reverse('toggle_user_status', args=[self.target_user.pk])

        response = self.client.post(url)
        self.assertRedirects(response, reverse('manage_users'))

        self.target_user.refresh_from_db()
        self.assertFalse(self.target_user.is_active)

    def test_toggle_activate(self):
        """Test activating an inactive user."""
        self.target_user.is_active = False
        self.target_user.save()

        self.client.login(username='superuser', password='password123')
        url = reverse('toggle_user_status', args=[self.target_user.pk])

        response = self.client.post(url)
        self.assertRedirects(response, reverse('manage_users'))

        self.target_user.refresh_from_db()
        self.assertTrue(self.target_user.is_active)

    def test_prevent_self_deactivation(self):
        """Ensure users cannot deactivate themselves."""
        self.client.login(username='superuser', password='password123')
        url = reverse('toggle_user_status', args=[self.superuser.pk])

        self.client.post(url)

        self.superuser.refresh_from_db()
        self.assertTrue(self.superuser.is_active)

    def test_prevent_staff_deactivating_superuser(self):
        """Ensure staff cannot deactivate superusers."""
        self.client.login(username='staff', password='password123')
        url = reverse('toggle_user_status', args=[self.superuser.pk])

        self.client.post(url)

        self.superuser.refresh_from_db()
        self.assertTrue(self.superuser.is_active)

    def test_staff_can_deactivate_regular_user(self):
        """Ensure staff can deactivate regular users."""
        self.client.login(username='staff', password='password123')
        url = reverse('toggle_user_status', args=[self.target_user.pk])

        self.client.post(url)

        self.target_user.refresh_from_db()
        self.assertFalse(self.target_user.is_active)
