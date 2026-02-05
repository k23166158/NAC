from django.db import models


from resolveme import settings
from .ticket import Ticket


class TicketMessage(models.Model):
   """Model representing a message within a support ticket."""
   id = models.AutoField(primary_key=True)
   ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name="messages")
   body = models.TextField()
   sender = models.ForeignKey(
      settings.AUTH_USER_MODEL,
      on_delete=models.CASCADE,
      null=True,
      blank=True,
      related_name="ticket_messages",
      db_column="sender",)
   created_at = models.DateTimeField(auto_now_add=True)
   edited_at = models.DateTimeField(auto_now=True)
   edited = models.BooleanField(default=False)

   hidden = models.BooleanField(default=False)

   class Meta:
      """Meta information for the TicketMessage model."""
      db_table = "ticket_messages"
      ordering = ["-edited_at"]

   def __str__(self):
      """String representation of the TicketMessage instance."""
      return f"Message {self.id} for Ticket {self.ticket.id} by User {self.sender.id}"