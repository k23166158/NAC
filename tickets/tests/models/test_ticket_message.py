from django.test import TestCase
from django.contrib.auth import get_user_model
from django.http import Http404
from tickets.models import Ticket, TicketMessage

User = get_user_model()

class TicketMessageModelTests(TestCase):
    """Tests for the TicketMessage model."""
    
    def setUp(self):
        """Set up a user and a ticket for testing."""
        self.user = User.objects.create_user(
            username='msguser', 
            password='password123',
            email='msg@example.com',
            first_name='Message',
            last_name='Sender'
        )
        self.ticket = Ticket.objects.create(
            title="Test Ticket",
            created_by=self.user
        )

    def test_message_creation_and_str(self):
        """Test creation of a message and its string representation."""
        message = TicketMessage.objects.create(
            ticket=self.ticket,
            sender=self.user,
            body="This is a test message."
        )

        self.assertEqual(message.body, "This is a test message.")
        self.assertEqual(message.ticket, self.ticket)
        self.assertEqual(message.sender, self.user)
        self.assertIsNotNone(message.created_at)
        self.assertIsNotNone(message.edited_at)
        self.assertFalse(message.edited)

        expected_str = f"Message {message.id} for Ticket {self.ticket.id} by User {self.user.id}"
        self.assertEqual(str(message), expected_str)

    def test_ordering(self):
        """Test that messages are ordered by created_at descending (newest first in default)."""
        m1 = TicketMessage.objects.create(ticket=self.ticket, sender=self.user, body="First")
        m2 = TicketMessage.objects.create(ticket=self.ticket, sender=self.user, body="Second")

        messages = list(TicketMessage.objects.all())
        self.assertEqual(messages[0], m2)
        self.assertEqual(messages[1], m1)

    def test_edited_flag_and_edited_at(self):
        """Test that editing a message sets edited=True and updates edited_at."""
        message = TicketMessage.objects.create(
            ticket=self.ticket,
            sender=self.user,
            body="Original",
        )
        self.assertFalse(message.edited)
        original_edited_at = message.edited_at

        message.body = "Updated"
        message.edited = True
        message.save()

        message.refresh_from_db()
        self.assertTrue(message.edited)
        self.assertEqual(message.body, "Updated")
        self.assertGreaterEqual(message.edited_at, original_edited_at)

    def test_create_system_message(self):
        """create_system_message should write sender-less system messages."""
        msg = TicketMessage.create_system_message(self.ticket, "System note")
        self.assertEqual(msg.ticket, self.ticket)
        self.assertIsNone(msg.sender)
        self.assertEqual(msg.body, "System note")

    def test_add_user_message_success_and_blank(self):
        """add_user_message should create for non-blank body and skip blank."""
        created = TicketMessage.add_user_message(self.ticket, self.user, "  hello ")
        self.assertIsNotNone(created)
        self.assertEqual(created.body, "hello")
        self.assertIsNone(TicketMessage.add_user_message(self.ticket, self.user, "   "))

    def test_update_user_message_success_and_empty_body(self):
        """update_user_message should update body/edited and no-op on empty body."""
        msg = TicketMessage.objects.create(ticket=self.ticket, sender=self.user, body="old")
        updated = TicketMessage.update_user_message(self.ticket, msg.id, self.user, "new")
        updated.refresh_from_db()
        self.assertEqual(updated.body, "new")
        self.assertTrue(updated.edited)

        no_change = TicketMessage.update_user_message(self.ticket, msg.id, self.user, "")
        self.assertIsNone(no_change)

    def test_hide_user_message_and_non_owner_raises(self):
        """hide_user_message should hide own message and reject non-owner."""
        msg = TicketMessage.objects.create(ticket=self.ticket, sender=self.user, body="hide me")
        hidden = TicketMessage.hide_user_message(self.ticket, msg.id, self.user)
        hidden.refresh_from_db()
        self.assertTrue(hidden.hidden)

        other = User.objects.create_user(
            username="othermsg",
            password="password123",
            email="othermsg@example.com",
            first_name="Other",
            last_name="User",
        )
        with self.assertRaises(Http404):
            TicketMessage.hide_user_message(self.ticket, msg.id, other)
