from django.test import TestCase
from django.contrib.auth import get_user_model
from django.db import IntegrityError

from tickets.models import Ticket
from tickets.models.ticket_participant import TicketParticipant  # adjust if needed

User = get_user_model()


class TicketParticipantModelTests(TestCase):
    """Tests for the TicketParticipant model."""

    def setUp(self):
        """Set up users + a ticket for testing."""
        mapping = [
            ("creator", "creator", "Ticket", "Owner", False),
            ("staff1", "teacher1", "Teacher", "One", True),
            ("staff2", "teacher2", "Teacher", "Two", True),
        ]
        for attr, username, fname, lname, is_staff in mapping:
            u = User.objects.create_user(username=username, password="password123",
                                         email=f"{username}@example.com",
                                         first_name=fname, last_name=lname, is_staff=is_staff)
            setattr(self, attr, u)
        self.ticket = Ticket.objects.create(title="Test Ticket", created_by=self.creator)

    def test_participant_creation_and_str(self):
        """Test creation of a participant and its string representation."""
        tp = TicketParticipant.objects.create(
            ticket=self.ticket,
            user=self.staff1,
            added_by=self.staff2,
        )

        self.assertEqual(tp.ticket, self.ticket)
        self.assertEqual(tp.user, self.staff1)
        self.assertEqual(tp.added_by, self.staff2)
        self.assertIsNotNone(tp.added_at)

        expected_str = f"Ticket #{self.ticket.id} participant: {self.staff1.id}"
        self.assertEqual(str(tp), expected_str)

    def test_unique_together_prevents_duplicate_participant(self):
        """A (ticket, user) pair should not be insertable twice."""
        TicketParticipant.objects.create(ticket=self.ticket, user=self.staff1, added_by=self.staff2)

        with self.assertRaises(IntegrityError):
            TicketParticipant.objects.create(ticket=self.ticket, user=self.staff1, added_by=self.staff2)

    def test_related_name_ticket_participants(self):
        """Ticket.participants related_name should return TicketParticipant rows."""
        tp = TicketParticipant.objects.create(ticket=self.ticket, user=self.staff1, added_by=self.staff2)

        # Because related_name="participants" on ticket ForeignKey
        participants = self.ticket.participants.all()
        self.assertEqual(participants.count(), 1)
        self.assertEqual(participants.first().id, tp.id)

    def test_related_name_user_ticket_participations(self):
        """User.ticket_participations related_name should return TicketParticipant rows."""
        tp = TicketParticipant.objects.create(ticket=self.ticket, user=self.staff1, added_by=self.staff2)

        qs = self.staff1.ticket_participations.all()
        self.assertEqual(qs.count(), 1)
        self.assertEqual(qs.first().id, tp.id)

    def test_added_by_can_be_null_and_set_null_on_delete(self):
        """
        added_by uses SET_NULL, so if the 'adder' user is deleted,
        the participant row remains and added_by becomes NULL.
        """
        tp = TicketParticipant.objects.create(ticket=self.ticket, user=self.staff1, added_by=self.staff2)

        # Delete the user who added the participant
        self.staff2.delete()

        tp.refresh_from_db()
        self.assertIsNone(tp.added_by)

    def test_cascade_delete_ticket_deletes_participants(self):
        """Deleting the ticket should cascade-delete TicketParticipant rows."""
        TicketParticipant.objects.create(ticket=self.ticket, user=self.staff1, added_by=self.staff2)
        self.assertEqual(TicketParticipant.objects.count(), 1)

        self.ticket.delete()
        self.assertEqual(TicketParticipant.objects.count(), 0)

    def test_cascade_delete_user_deletes_participations(self):
        """Deleting the participant user should delete their TicketParticipant rows."""
        TicketParticipant.objects.create(ticket=self.ticket, user=self.staff1, added_by=self.staff2)
        self.assertEqual(TicketParticipant.objects.count(), 1)

        self.staff1.delete()
        self.assertEqual(TicketParticipant.objects.count(), 0)
