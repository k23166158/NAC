from django.db import models


from resolveme import settings
from .ticket import Ticket


class TicketMessage(models.Model):
   id = models.AutoField(primary_key=True)
   ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE)
   body = models.TextField()
   sender = models.ForeignKey(
       settings.AUTH_USER_MODEL,
       on_delete=models.CASCADE,
       related_name="ticket_messages",
       db_column="sender",)
   timestamp = models.DateTimeField(auto_now_add=True)


   class Meta:
       db_table = "ticket_messages"
       ordering = ["-timestamp"]
  
   def __str__(self):
       return f"Message {self.id} for Ticket {self.ticket.id} by User {self.sender.id}"