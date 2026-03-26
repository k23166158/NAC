from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone

from tickets.models.notification import Notification

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

    def test_notifications_view_paginates_results(self):
        """Notifications page should split results across pages."""
        for index in range(11):
            Notification.objects.create(
                user=self.user,
                notification_type=Notification.NotificationType.TICKET_CREATED,
                short_message=f"Notification {index}",
            )

        self.client.login(username="testuser", password="password123")
        page_one = self.client.get(self.url)
        page_two = self.client.get(self.url, {"page": 2})

        self.assertEqual(len(page_one.context["notifications"]), 10)
        self.assertEqual(page_one.context["page_obj"].number, 1)
        self.assertEqual(len(page_two.context["notifications"]), 1)
        self.assertEqual(page_two.context["page_obj"].number, 2)

    def test_notifications_older_than_thirty_days_are_deleted(self):
        """Notifications older than thirty days should be removed on page load."""
        fresh = Notification.objects.create(
            user=self.user,
            notification_type=Notification.NotificationType.TICKET_CREATED,
            short_message="Fresh notification",
        )
        expired = Notification.objects.create(
            user=self.user,
            notification_type=Notification.NotificationType.TICKET_CREATED,
            short_message="Expired notification",
        )
        Notification.objects.filter(pk=expired.pk).update(
            created_at=timezone.now() - timedelta(days=31),
        )

        self.client.login(username="testuser", password="password123")
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(Notification.objects.filter(pk=fresh.pk).exists())
        self.assertFalse(Notification.objects.filter(pk=expired.pk).exists())
