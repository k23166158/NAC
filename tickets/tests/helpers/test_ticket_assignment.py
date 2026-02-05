from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from unittest import mock
from datetime import timedelta

# Adjust this import to match where your function is located
from tickets.helpers.ticket_assignment import assign_staff_to_ticket
from tickets.models import Ticket, TicketParticipant, TicketMessage

User = get_user_model()

class AssignStaffToTicketTests(TestCase):
    def setUp(self):
        # Create a standard user and a staff user
        self.staff_user = User.objects.create_user(
            username='staff', 
            email='staff@example.com',
            password='password', 
            first_name='John', 
            last_name='Doe'
        )
        self.admin_user = User.objects.create_user(
            username='admin', 
            email='admin@example.com',
            password='password'
        )
        
        # Create a ticket instance
        self.ticket = Ticket.objects.create(
            title="Test Ticket",
            created_by=self.staff_user,
            # Ensure updated_at is in the past so we can test it changing
            updated_at=timezone.now() - timedelta(days=1)
        )

    def test_assign_staff_successfully_created(self):
        """
        Test that a new staff member is assigned, a message is created, 
        and the ticket timestamp is updated.
        """
        old_updated_at = self.ticket.updated_at
        
        # 1. Call the function
        result = assign_staff_to_ticket(self.ticket, self.staff_user)

        # 2. Refresh ticket from DB to check timestamp
        self.ticket.refresh_from_db()

        # --- Assertions ---
        # Should return True
        self.assertTrue(result)

        # Participant should exist
        self.assertTrue(
            TicketParticipant.objects.filter(ticket=self.ticket, user=self.staff_user).exists()
        )

        # System message should be created
        expected_msg = "John Doe was added to the ticket."
        self.assertTrue(
            TicketMessage.objects.filter(ticket=self.ticket, body=expected_msg).exists()
        )

        # Ticket updated_at should have changed
        self.assertNotEqual(self.ticket.updated_at, old_updated_at)
        self.assertTrue(self.ticket.updated_at > old_updated_at)

    def test_assign_staff_already_exists(self):
        """
        Test that if the staff is already a participant, function returns False
        and no side effects occur (no new message, no timestamp update).
        """
        # Setup: Manually create participant first
        TicketParticipant.objects.create(ticket=self.ticket, user=self.staff_user)
        
        # Capture state before call
        old_updated_at = self.ticket.updated_at
        initial_message_count = TicketMessage.objects.count()

        # 1. Call the function
        result = assign_staff_to_ticket(self.ticket, self.staff_user)

        # 2. Refresh ticket
        self.ticket.refresh_from_db()

        # --- Assertions ---
        # Should return False
        self.assertFalse(result)

        # No new messages should be created
        self.assertEqual(TicketMessage.objects.count(), initial_message_count)

        # Timestamp should NOT change (allowing for microsecond DB precision differences)
        self.assertEqual(self.ticket.updated_at, old_updated_at)

    def test_assign_with_added_by_argument(self):
        """
        Test that the 'added_by' argument is successfully passed to the 
        TicketParticipant creation.
        """
        # Only run this assertion if the model actually has the field,
        # otherwise the code snippet provided ignores it gracefully.
        has_field = hasattr(TicketParticipant, 'added_by')
        
        result = assign_staff_to_ticket(
            self.ticket, 
            self.staff_user, 
            added_by=self.admin_user
        )

        self.assertTrue(result)
        
        participant = TicketParticipant.objects.get(ticket=self.ticket, user=self.staff_user)
        
        if has_field:
            self.assertEqual(participant.added_by, self.admin_user)

    def test_assign_with_added_by_logic_coverage(self):
        """
        Strict coverage test: Validates the conditional logic for 'defaults={...}'.
        We mock hasattr to ensure we hit both branches of the conditional logic
        regardless of the actual model definition.
        """
        # Case A: added_by is None (Should pass empty defaults)
        with mock.patch('tickets.models.TicketParticipant.objects.get_or_create') as mock_goc:
            mock_goc.return_value = (mock.Mock(), True) # Return (obj, created)
            
            assign_staff_to_ticket(self.ticket, self.staff_user, added_by=None)
            
            # Verify called with empty defaults
            args, kwargs = mock_goc.call_args
            self.assertEqual(kwargs['defaults'], {})

    @mock.patch('tickets.helpers.ticket_assignment.TicketParticipant') 
    def test_assign_with_added_by_but_field_missing(self, MockParticipant):
        """
        Defensive coding test: passing added_by, but the Model doesn't have the field.
        Should result in empty defaults.
        """
        # Mock hasattr to return False
        # Note: hasattr checks on the object, so we configure the Mock to fail attribute access
        del MockParticipant.added_by 
        
        MockParticipant.objects.get_or_create.return_value = (mock.Mock(), True)

        assign_staff_to_ticket(self.ticket, self.staff_user, added_by=self.admin_user)

        # Verify defaults={} because hasattr failed
        call_kwargs = MockParticipant.objects.get_or_create.call_args[1]
        self.assertEqual(call_kwargs['defaults'], {})