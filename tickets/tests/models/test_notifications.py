from django.utils import timezone

from django.test import TestCase
from django.contrib.auth import get_user_model
from tickets.models.notification import Notification

User = get_user_model()

class NotificationModelTest(TestCase):
    """Tests for the Notification model."""

    def _create_user(self, username):
        """Create a user with a unique email derived from username."""
        return User.objects.create_user(
            username=username,
            email=f"{username}@example.com",
            password="password123",
        )

    def _create_notification(self, user, message, *, kind, is_read=False):
        """Create a notification for a user with the provided details."""
        return Notification.objects.create(
            user=user,
            notification_type=kind,
            short_message=message,
            is_read=is_read,
        )

    def test_notification_str_method(self):
        """Test that the string representation of a notification is correct."""
        user = User.objects.create_user(username='testuser', password='password123')
        notification = Notification.objects.create(
            user=user,
            notification_type=Notification.NotificationType.TICKET_CREATED,
            short_message="A new ticket was created"
        )
        self.assertEqual(str(notification), "TICKET_CREATED for testuser")

    def test_recent_for_user_returns_only_user_notifications(self):
        """recent_for_user should scope notifications to the requested user."""
        user = self._create_user("target")
        other = self._create_user("other")
        first = self._create_notification(
            user,
            "First",
            kind=Notification.NotificationType.TICKET_CREATED,
            is_read=True,
        )
        second = self._create_notification(
            user,
            "Second",
            kind=Notification.NotificationType.NEW_MESSAGE,
        )
        self._create_notification(
            other,
            "Ignored",
            kind=Notification.NotificationType.NEW_MESSAGE,
        )

        notifications = list(Notification.recent_for_user(user))

        self.assertEqual(notifications, [second, first])

    def test_mark_all_read_for_updates_unread_notifications(self):
        """mark_all_read_for should mark only the user's unread notifications."""
        user = self._create_user("reader")
        other = self._create_user("otherreader")
        unread = self._create_notification(
            user,
            "Unread",
            kind=Notification.NotificationType.TICKET_CREATED,
        )
        self._create_notification(
            other,
            "Other unread",
            kind=Notification.NotificationType.TICKET_CREATED,
        )

        updated = Notification.mark_all_read_for(user)
        unread.refresh_from_db()

        self.assertEqual(updated, 1)
        self.assertTrue(unread.is_read)
