from django.contrib.auth.models import AnonymousUser
from django.test import RequestFactory, TestCase
from django.contrib.auth import get_user_model

from tickets.context_processors import notifications_context
from tickets.models import Notification

User = get_user_model()


class NotificationsContextProcessorTests(TestCase):
    """Tests for notifications context processor."""

    def setUp(self):
        """Set up request factory and a user."""
        self.factory = RequestFactory()
        self.user = User.objects.create_user(
            username="cpuser",
            email="cpuser@example.com",
            password="password123",
            first_name="CP",
            last_name="User",
        )

    def test_returns_zero_for_anonymous(self):
        """Anonymous users should receive zero unread notifications."""
        request = self.factory.get("/")
        request.user = AnonymousUser()
        result = notifications_context(request)
        self.assertEqual(result["unread_notifications_count"], 0)

    def test_returns_unread_count_for_authenticated_user(self):
        """Authenticated users should get their unread notification count."""
        Notification.objects.create(
            user=self.user,
            notification_type=Notification.NotificationType.TICKET_CREATED,
            short_message="one",
        )
        Notification.objects.create(
            user=self.user,
            notification_type=Notification.NotificationType.TICKET_CREATED,
            short_message="two",
            is_read=True,
        )
        request = self.factory.get("/")
        request.user = self.user
        result = notifications_context(request)
        self.assertEqual(result["unread_notifications_count"], 1)
