from django.utils import timezone

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

    def test_for_display_for_returns_only_user_notifications(self):
        """for_display_for should scope notifications to the requested user."""
        user = User.objects.create_user(
            username="target",
            email="target@example.com",
            password="password123",
        )
        other = User.objects.create_user(
            username="other",
            email="other@example.com",
            password="password123",
        )
        first = Notification.objects.create(
            user=user,
            notification_type=Notification.NotificationType.TICKET_CREATED,
            short_message="First",
            is_read=True,
        )
        second = Notification.objects.create(
            user=user,
            notification_type=Notification.NotificationType.NEW_MESSAGE,
            short_message="Second",
            is_read=False,
        )
        Notification.objects.create(
            user=other,
            notification_type=Notification.NotificationType.NEW_MESSAGE,
            short_message="Ignored",
        )

        notifications = list(Notification.for_display_for(user))

        self.assertEqual(notifications, [second, first])

    def test_mark_all_read_for_updates_unread_notifications(self):
        """mark_all_read_for should mark only the user's unread notifications."""
        user = User.objects.create_user(
            username="reader",
            email="reader@example.com",
            password="password123",
        )
        other = User.objects.create_user(
            username="otherreader",
            email="otherreader@example.com",
            password="password123",
        )
        unread = Notification.objects.create(
            user=user,
            notification_type=Notification.NotificationType.TICKET_CREATED,
            short_message="Unread",
            is_read=False,
        )
        Notification.objects.create(
            user=other,
            notification_type=Notification.NotificationType.TICKET_CREATED,
            short_message="Other unread",
            is_read=False,
        )

        updated = Notification.mark_all_read_for(user)
        unread.refresh_from_db()

        self.assertEqual(updated, 1)
        self.assertTrue(unread.is_read)
