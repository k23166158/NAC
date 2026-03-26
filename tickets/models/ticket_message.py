from django.db import models
from django.shortcuts import get_object_or_404


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
      ordering = ["-created_at"]

   @classmethod
   def create_system_message(cls, ticket, body):
      """Create a system message without a sender."""
      return cls.objects.create(ticket=ticket, sender=None, body=body)

   @classmethod
   def add_user_message(cls, ticket, user, body):
      """Create a user reply message for a ticket."""
      from tickets.models.notification import Notification
      from tickets.helpers.notifications import notify_ticket_participants

      text = (body or "").strip()
      if not text:
         return None
      message = cls.objects.create(ticket=ticket, sender=user, body=text)
      ticket.touch()
      notify_ticket_participants(
         ticket,
         actor=user,
         notification_type=Notification.NotificationType.NEW_MESSAGE,
      )
      return message

   @classmethod
   def update_user_message(cls, ticket, message_id, user, body):
      """Update a sender-owned visible message."""
      message = get_object_or_404(
         cls,
         id=message_id,
         ticket=ticket,
         sender=user,
         hidden=False,
      )
      if not body:
         return None
      message.body = body
      message.edited = True
      message.save()
      ticket.touch()
      return message

   @classmethod
   def hide_user_message(cls, ticket, message_id, user):
      """Soft-delete a sender-owned message."""
      message = get_object_or_404(
         cls,
         id=message_id,
         ticket=ticket,
         sender=user,
      )
      message.hidden = True
      message.save(update_fields=["hidden", "edited_at"])
      ticket.touch()
      return message

   def __str__(self):
      """String representation of the TicketMessage instance."""
      return f"Message {self.id} for Ticket {self.ticket.id} by User {self.sender.id}"