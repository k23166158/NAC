from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase, override_settings

from tickets.helpers.notifications import notify_ticket_reply
from tickets.models import Notification, Ticket, TicketParticipant

User = get_user_model()


class NotifyTicketReplyTests(TestCase):
    """Tests for ticket reply notification helper."""

    def setUp(self):
        """Set up users and a sample ticket."""
        self.actor = User.objects.create_user(
            username="actor1",
            email="actor1@example.com",
            password="password123",
            first_name="Actor",
            last_name="One",
        )
        self.other = User.objects.create_user(
            username="other1",
            email="other1@example.com",
            password="password123",
            first_name="Other",
            last_name="One",
        )
        self.no_email = User.objects.create_user(
            username="noemail1",
            email="",
            password="password123",
            first_name="No",
            last_name="Email",
        )
        self.ticket = Ticket.objects.create(title="Help", created_by=self.actor)
        TicketParticipant.objects.create(ticket=self.ticket, user=self.other)
        TicketParticipant.objects.create(ticket=self.ticket, user=self.no_email)

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    def test_creates_notifications_and_sends_emails(self):
        """Helper should notify recipients and email users with valid emails."""
        notify_ticket_reply(self.ticket, self.actor, "body text")
        reply_type = Notification.NotificationType.TICKET_REPLY
        self.assertTrue(Notification.objects.filter(user=self.other, notification_type=reply_type).exists())
        self.assertTrue(Notification.objects.filter(user=self.no_email, notification_type=reply_type).exists())
        self.assertFalse(Notification.objects.filter(user=self.actor, notification_type=reply_type).exists())
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["other1@example.com"])
