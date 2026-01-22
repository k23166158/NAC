from django.test import TestCase
from django.contrib.auth import get_user_model
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
        self.assertIsNotNone(message.timestamp)

        expected_str = f"Message {message.id} for Ticket {self.ticket.id} by User {self.user.id}"
        self.assertEqual(str(message), expected_str)

    def test_ordering(self):
        """Test that messages are ordered by timestamp descending."""
        m1 = TicketMessage.objects.create(ticket=self.ticket, sender=self.user, body="First")
        m2 = TicketMessage.objects.create(ticket=self.ticket, sender=self.user, body="Second")
        
        messages = list(TicketMessage.objects.all())
        self.assertEqual(messages[0], m2)
        self.assertEqual(messages[1], m1)