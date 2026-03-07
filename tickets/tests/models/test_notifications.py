from django.test import TestCase
from django.contrib.auth import get_user_model
from tickets.models.notification import Notification

User = get_user_model()

class NotificationModelTest(TestCase):
    """Tests for the Notification model."""

    def test_notification_str_method(self):
        """Test that the string representation of a notification is correct."""
        user = User.objects.create_user(username='testuser', password='password123')
        notification = Notification.objects.create(
            user=user,
            notification_type=Notification.NotificationType.TICKET_CREATED,
            short_message="A new ticket was created"
        )
        self.assertEqual(str(notification), "TICKET_CREATED for testuser")