from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from tickets.models import Notification, Ticket

User = get_user_model()


class NotificationViewTests(TestCase):
    """Tests for the NotificationView to ensure it behaves correctly for authenticated and unauthenticated users."""
    def setUp(self):
        """Set up a test user and the URL for the notifications view."""
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="password123",
            first_name="Test", last_name="User",
        )
        self.actor = User.objects.create_user(
            username="actor", email="actor@example.com", password="password123",
            first_name="Actor", last_name="User",
        )
        self.ticket = Ticket.objects.create(title="Test Ticket", created_by=self.user)
        self.url = reverse("notifications")

    def _login(self):
        """Authenticate the default test user."""
        self.client.login(username="testuser", password="password123")

    def _create_reply_notification(self):
        """Create a ticket reply notification for the default user."""
        return Notification.objects.create(
            user=self.user,
            actor=self.actor,
            target_object=self.ticket,
            notification_type=Notification.NotificationType.TICKET_REPLY,
            short_message="Actor User replied to your ticket.",
            long_message="A new response was posted.",
        )

    def test_notifications_view_requires_login(self):
        """Ensure that the notifications view redirects to the login page for unauthenticated users."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)

    def test_notifications_view_logged_in(self):
        """Ensure that the notifications view loads successfully for authenticated users."""
        self._login()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_notifications_view_uses_correct_template(self):
        """Ensure that the notifications view uses the correct template."""
        self._login()
        response = self.client.get(self.url)
        self.assertTemplateUsed(response, "notifications.html")

    def test_notifications_view_lists_notifications(self):
        """Notifications should be listed for the logged-in user."""
        self._create_reply_notification()
        self._login()
        response = self.client.get(self.url)
        self.assertContains(response, "replied to your ticket")

    def test_open_marks_notification_read(self):
        """Opening a notification marks it as read and redirects to ticket thread."""
        notification = self._create_reply_notification()
        self._login()
        response = self.client.get(
            reverse("notification_open", kwargs={"notification_id": notification.id})
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn(str(self.ticket.uuid), response.url)
        notification.refresh_from_db()
        self.assertTrue(notification.is_read)

    def test_open_without_target_redirects_notifications(self):
        """Opening notification without target should redirect to notifications list."""
        notification = Notification.objects.create(
            user=self.user,
            actor=self.actor,
            notification_type=Notification.NotificationType.TICKET_CREATED,
            short_message="Created",
            long_message="Created long",
        )
        self._login()
        response = self.client.get(reverse("notification_open", kwargs={"notification_id": notification.id}))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("notifications"))

    def test_open_already_read_still_redirects(self):
        """Already-read notifications should still redirect to their ticket."""
        notification = self._create_reply_notification()
        notification.is_read = True
        notification.save(update_fields=["is_read"])
        self._login()
        response = self.client.get(reverse("notification_open", kwargs={"notification_id": notification.id}))
        self.assertEqual(response.status_code, 302)
        self.assertIn(str(self.ticket.uuid), response.url)
