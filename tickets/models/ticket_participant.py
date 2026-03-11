# tickets/models/ticket_participant.py
from django.db import models
from django.conf import settings
from .ticket import Ticket

class TicketParticipant(models.Model):
    """Model representing a participant (staff member) in a support ticket."""
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name="participants")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="ticket_participations")
    added_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="participants_added")
    added_at = models.DateTimeField(auto_now_add=True)
    last_read_at = models.DateTimeField(null=True, blank=True)
    removed_self = models.BooleanField(default=False, help_text="Whether the user removed themselves from the ticket")
    
    class Meta:
        """Meta information for the TicketParticipant model."""
        db_table = "ticket_participants"
        unique_together = ("ticket", "user")

    @classmethod
    def defaults_for_actor(cls, actor):
        """Return defaults used when creating a participant via an actor action."""
        return {"added_by": actor} if any(f.name == "added_by" for f in cls._meta.fields) else {}

    @classmethod
    def has_participant(cls, ticket, user):
        """Return whether a user is already a participant for a ticket."""
        return cls.objects.filter(ticket=ticket, user=user).exists()

    @classmethod
    def add_participant(cls, ticket, user, *, actor=None, defaults=None):
        """Create participant row with optional actor-derived defaults."""
        participant_defaults = cls.defaults_for_actor(actor) if defaults is None else defaults
        return cls.objects.create(ticket=ticket, user=user, **participant_defaults)

    @classmethod
    def remove_participant(cls, ticket, user):
        """Remove a participant from a ticket."""
        cls.objects.filter(ticket=ticket, user=user).delete()

    @classmethod
    def assign_staff(cls, ticket, staff_user, *, added_by=None):
        """Assign a staff user with standard ticket side effects."""
        from tickets.helpers.ticket_assignment import assign_staff_to_ticket

        return assign_staff_to_ticket(ticket=ticket, staff_user=staff_user, added_by=added_by)

    def __str__(self):
        """String representation of the TicketParticipant instance."""
        return f"Ticket #{self.ticket_id} participant: {self.user_id}"
