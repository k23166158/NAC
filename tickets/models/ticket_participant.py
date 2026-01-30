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

    class Meta:
        """Meta information for the TicketParticipant model."""
        db_table = "ticket_participants"
        unique_together = ("ticket", "user")

    def __str__(self):
        """String representation of the TicketParticipant instance."""
        return f"Ticket #{self.ticket_id} participant: {self.user_id}"
