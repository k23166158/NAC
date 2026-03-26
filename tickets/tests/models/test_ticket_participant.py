from django.test import TestCase
from django.contrib.auth import get_user_model
from django.db import IntegrityError
from types import SimpleNamespace

from tickets.models import Ticket, TicketMessage
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

    def test_defaults_for_actor(self):
        """defaults_for_actor should include added_by mapping."""
        defaults = TicketParticipant.defaults_for_actor(self.staff2)
        self.assertEqual(defaults, {"added_by": self.staff2})

    def test_defaults_for_actor_without_added_by_field(self):
        """defaults_for_actor should return empty dict when added_by field is absent."""
        original_fields = TicketParticipant._meta.fields
        try:
            # Simulate a model definition without an added_by field
            TicketParticipant._meta.fields = [SimpleNamespace(name="something_else")]
            defaults = TicketParticipant.defaults_for_actor(self.staff2)
            self.assertEqual(defaults, {})
        finally:
            TicketParticipant._meta.fields = original_fields

    def test_has_add_and_remove_participant_helpers(self):
        """Participant helper methods should create/check/remove participants."""
        self.assertFalse(TicketParticipant.has_participant(self.ticket, self.staff1))
        TicketParticipant.add_participant(self.ticket, self.staff1, actor=self.staff2)
        self.assertTrue(TicketParticipant.has_participant(self.ticket, self.staff1))
        tp = TicketParticipant.objects.get(ticket=self.ticket, user=self.staff1)
        self.assertEqual(tp.added_by, self.staff2)
        TicketParticipant.remove_participant(self.ticket, self.staff1)
        self.assertFalse(TicketParticipant.has_participant(self.ticket, self.staff1))

    def test_add_participant_restores_removed_self_flag(self):
        """add_participant should clear removed_self on existing participant records."""
        # Create a participant who has previously removed themselves
        tp = TicketParticipant.objects.create(
            ticket=self.ticket,
            user=self.staff1,
            added_by=self.staff2,
            removed_self=True,
        )
        # Re-add the same participant via helper
        returned = TicketParticipant.add_participant(self.ticket, self.staff1, actor=self.staff2)
        tp.refresh_from_db()
        self.assertEqual(returned.id, tp.id)
        self.assertFalse(tp.removed_self)

    def test_assign_staff_creates_participant_and_system_message(self):
        """assign_staff should apply ticket-assignment side effects."""
        created = TicketParticipant.assign_staff(self.ticket, self.staff1, added_by=self.staff2)
        self.assertTrue(created)
        self.assertTrue(TicketParticipant.objects.filter(ticket=self.ticket, user=self.staff1).exists())
        self.assertTrue(
            TicketMessage.objects.filter(
                ticket=self.ticket,
                body__contains=f"{self.staff1.get_full_name()} was added to the ticket.",
                sender=None,
            ).exists()
        )

    def test_mark_removed_self_sets_flag(self):
        """mark_removed_self should update and return the participant."""
        participant = TicketParticipant.objects.create(
            ticket=self.ticket,
            user=self.staff1,
            added_by=self.staff2,
        )

        returned = TicketParticipant.mark_removed_self(self.ticket, self.staff1)
        participant.refresh_from_db()

        self.assertEqual(returned.pk, participant.pk)
        self.assertTrue(participant.removed_self)
