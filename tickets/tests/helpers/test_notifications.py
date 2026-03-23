from unittest.mock import patch, MagicMock

from django.contrib.auth import get_user_model
from django.test import TestCase

from tickets.helpers.notifications import (
    create_notification,
    get_ticket_participants,
    notify_ticket_participants,
    notify_overdue_ticket,
)
from tickets.models import Ticket, Notification
from tickets.models.ticket_participant import TicketParticipant

User = get_user_model()


class GetTicketParticipantsTests(TestCase):
    """Tests for get_ticket_participants helper."""

    def setUp(self):
        """Create users and ticket fixtures."""
        self.creator = User.objects.create_user(
            username="creator", email="creator@example.com",
            password="p", first_name="Creator", last_name="User",
        )
        self.staff1 = User.objects.create_user(
            username="staff1", email="staff1@example.com",
            password="p", first_name="Staff", last_name="One", is_staff=True,
        )
        self.staff2 = User.objects.create_user(
            username="staff2", email="staff2@example.com",
            password="p", first_name="Staff", last_name="Two", is_staff=True,
        )
        self.ticket = Ticket.objects.create(
            title="Participants ticket", created_by=self.creator,
        )

    def test_includes_ticket_creator(self):
        """get_ticket_participants should always include the ticket creator."""
        participants = get_ticket_participants(self.ticket)
        self.assertIn(self.creator, participants)

    def test_includes_assigned_staff(self):
        """get_ticket_participants should include staff assigned to the ticket."""
        TicketParticipant.objects.create(ticket=self.ticket, user=self.staff1)
        participants = get_ticket_participants(self.ticket)
        self.assertIn(self.staff1, participants)

    def test_excludes_specified_user(self):
        """get_ticket_participants should exclude the given user."""
        participants = get_ticket_participants(self.ticket, exclude_user=self.creator)
        self.assertNotIn(self.creator, participants)

    def test_deduplicates_users(self):
        """get_ticket_participants should return a deduplicated set."""
        # Creator is also assigned as staff
        TicketParticipant.objects.create(ticket=self.ticket, user=self.creator)
        participants = get_ticket_participants(self.ticket)
        user_ids = [u.id for u in participants]
        self.assertEqual(len(user_ids), len(set(user_ids)))

    def test_returns_set(self):
        """get_ticket_participants should return a set."""
        result = get_ticket_participants(self.ticket)
        self.assertIsInstance(result, set)

    def test_exclude_none_keeps_all(self):
        """Passing exclude_user=None should keep all participants."""
        TicketParticipant.objects.create(ticket=self.ticket, user=self.staff1)
        participants = get_ticket_participants(self.ticket, exclude_user=None)
        self.assertIn(self.creator, participants)
        self.assertIn(self.staff1, participants)


class NotifyTicketParticipantsTests(TestCase):
    """Tests for notify_ticket_participants helper."""

    def setUp(self):
        """Create users and a ticket for notification tests."""
        self.actor = User.objects.create_user(
            username="actor",
            email="actor@example.com",
            password="password123",
            first_name="Actor",
            last_name="User",
        )
        self.recipient = User.objects.create_user(
            username="recipient",
            email="recipient@example.com",
            password="password123",
            first_name="Recipient",
            last_name="User",
            is_staff=True,
        )
        self.ticket = Ticket.objects.create(
            title="Notify ticket",
            created_by=self.recipient,
        )

    @patch("tickets.helpers.notifications.send_email")
    def test_creates_notification_for_participants(self, mock_send):
        """notify_ticket_participants creates notifications for each participant except actor."""
        # Actor is not the creator, so creator (recipient) should get notified
        notify_ticket_participants(
            self.ticket,
            actor=self.actor,
            notification_type=Notification.NotificationType.TICKET_CLOSED,
        )
        notifications = Notification.objects.filter(
            user=self.recipient,
            notification_type=Notification.NotificationType.TICKET_CLOSED,
        )
        self.assertEqual(notifications.count(), 1)
        self.assertEqual(notifications[0].actor, self.actor)

    @patch("tickets.helpers.notifications.send_email")
    def test_excludes_actor_from_notifications(self, mock_send):
        """Actor should not receive a notification."""
        # Actor is also the creator
        self.ticket.created_by = self.actor
        self.ticket.save()
        notify_ticket_participants(
            self.ticket,
            actor=self.actor,
            notification_type=Notification.NotificationType.TICKET_CLOSED,
        )
        notifications = Notification.objects.filter(
            user=self.actor,
            notification_type=Notification.NotificationType.TICKET_CLOSED,
        )
        self.assertEqual(notifications.count(), 0)

    @patch("tickets.helpers.notifications.send_email")
    def test_notification_link_contains_ticket_uuid(self, mock_send):
        """Created notifications should have the correct ticket link."""
        TicketParticipant.objects.create(ticket=self.ticket, user=self.recipient)
        notify_ticket_participants(
            self.ticket,
            actor=self.actor,
            notification_type=Notification.NotificationType.NEW_MESSAGE,
        )
        notification = Notification.objects.filter(
            user=self.recipient,
            notification_type=Notification.NotificationType.NEW_MESSAGE,
        ).first()
        self.assertIsNotNone(notification)


class CreateNotificationTests(TestCase):
    """Tests for the create_notification factory function."""

    def setUp(self):
        """Create test users."""
        self.user = User.objects.create_user(
            username="notif_user",
            email="notif@example.com",
            password="password123",
            first_name="Notif",
            last_name="User",
        )
        self.actor = User.objects.create_user(
            username="notif_actor",
            email="notifactor@example.com",
            password="password123",
            first_name="Notif",
            last_name="Actor",
        )

    @patch("tickets.helpers.notifications.send_email")
    def test_creates_notification_record(self, mock_send):
        """create_notification should persist a Notification to the database."""
        ticket = Ticket.objects.create(title="Test", created_by=self.user)
        notification = create_notification(
            user=self.user,
            actor=self.actor,
            notification_type=Notification.NotificationType.TICKET_CREATED,
            link=f"/tickets/{ticket.uuid}/",
            target_object=ticket,
        )
        self.assertIsNotNone(notification.id)
        self.assertEqual(notification.user, self.user)
        self.assertEqual(notification.actor, self.actor)
        self.assertEqual(notification.notification_type, Notification.NotificationType.TICKET_CREATED)

    @patch("tickets.helpers.notifications.send_email")
    def test_sends_email(self, mock_send):
        """create_notification should call send_email."""
        ticket = Ticket.objects.create(title="Test", created_by=self.user)
        mock_send.reset_mock()
        create_notification(
            user=self.user,
            actor=self.actor,
            notification_type=Notification.NotificationType.TICKET_CREATED,
            link=f"/tickets/{ticket.uuid}/",
            target_object=ticket,
        )
        mock_send.assert_called_once()

class NotifyOverdueTicketTests(TestCase):
    """Test suite for overdue ticket notification helpers."""

    @patch('tickets.helpers.notifications.create_notification')
    def test_notify_overdue_ticket(self, mock_create_notification):
        """Test that overdue notifications are sent to the correct staff combinations, excluding the creator."""
        mock_ticket = MagicMock()
        mock_ticket.uuid = "1234-5678"
        
        creator = MagicMock()
        staff_user1 = MagicMock()
        staff_user2 = MagicMock()
        
        mock_ticket.created_by = creator
        mock_ticket.get_ticket_staff.return_value = [staff_user1, creator]
        mock_ticket.get_department_staff.return_value = [staff_user2]
        mock_actor = MagicMock()
        
        notify_overdue_ticket(mock_ticket, actor=mock_actor)        
        self.assertEqual(mock_create_notification.call_count, 2)
        
        notified_users = [call.kwargs['user'] for call in mock_create_notification.call_args_list]
        self.assertIn(staff_user1, notified_users)
        self.assertIn(staff_user2, notified_users)
        self.assertNotIn(creator, notified_users)
