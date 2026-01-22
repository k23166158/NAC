from django.test import TestCase
from django.contrib.auth import get_user_model
from tickets.models import Ticket

User = get_user_model()

class TicketModelTests(TestCase):
    """Test the Ticket model."""
    def setUp(self):
        """
        Set up data for the tests. 
        This runs before every single test method.
        """
        self.user = User.objects.create_user(
            username='testuser', 
            password='testpassword123',
            email='test@example.com',
            first_name='Test',
            last_name='User'
        )
        
        self.ticket = Ticket.objects.create(
            title="Test Server Issue",
            created_by=self.user
        )

    def test_ticket_creation_and_defaults(self):
        """Test that a ticket is created with the correct default values."""
        self.assertTrue(isinstance(self.ticket, Ticket))
        self.assertEqual(self.ticket.title, "Test Server Issue")
        self.assertEqual(self.ticket.created_by, self.user)
        self.assertEqual(self.ticket.status, Ticket.Status.OPEN)

    def test_str_representation(self):
        """Test the __str__ method matches the format '#{id} - {title}'."""
        string_representation = str(self.ticket)
        expected_format = f"#{self.ticket.id} - {self.ticket.title}"
        self.assertEqual(string_representation, expected_format)

    def test_status_choices(self):
        """Test that the Status TextChoices are correctly defined."""
        self.assertEqual(Ticket.Status.OPEN, 'open')
        self.assertEqual(Ticket.Status.PENDING, 'pending')
        self.assertEqual(Ticket.Status.CLOSED, 'closed')
        
        closed_ticket = Ticket.objects.create(
            title="Closed Ticket",
            created_by=self.user,
            status=Ticket.Status.CLOSED
        )
        self.assertEqual(closed_ticket.status, 'closed')

    def test_timestamps(self):
        """Test that created_at and updated_at are automatically set."""
        self.assertIsNotNone(self.ticket.created_at)
        self.assertIsNotNone(self.ticket.updated_at)
        
    def test_user_relationship(self):
        """Test the 'related_name' attribute allows reverse lookup."""
        user_tickets = self.user.tickets_created.all()
        
        self.assertIn(self.ticket, user_tickets)
        self.assertEqual(user_tickets.count(), 1)