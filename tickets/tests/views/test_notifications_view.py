from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model

User = get_user_model()


class NotificationViewTests(TestCase):
    """Tests for the NotificationView to ensure it behaves correctly for authenticated and unauthenticated users."""
    def setUp(self):
        """Set up a test user and the URL for the notifications view."""
        self.user = User.objects.create_user(
            username="testuser",
            password="password123"
        )
        self.url = reverse("notifications")

    def test_notifications_view_requires_login(self):
        """Ensure that the notifications view redirects to the login page for unauthenticated users."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)

    def test_notifications_view_logged_in(self):
        """Ensure that the notifications view loads successfully for authenticated users."""
        self.client.login(username="testuser", password="password123")
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_notifications_view_uses_correct_template(self):
        """Ensure that the notifications view uses the correct template."""
        self.client.login(username="testuser", password="password123")
        response = self.client.get(self.url)
        self.assertTemplateUsed(response, "notifications.html")
