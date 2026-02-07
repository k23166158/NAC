import uuid

from django.db import models
from django.conf import settings

from .ticket_message import TicketMessage
from .ticket import Ticket


class TicketMessageAttachment(models.Model):
    """ Represents a file attachment belonging to a ticket message. One message can have multiple attachments."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    ticket = models.ForeignKey(
        Ticket,
        on_delete=models.CASCADE,
        related_name="attachments",
    )

    message = models.ForeignKey(
        TicketMessage,
        on_delete=models.CASCADE,
        related_name="attachments",
    )

    file = models.FileField(upload_to="ticket_attachments/%Y/%m/%d/")

    original_name = models.CharField(max_length=255, blank=True)
    content_type = models.CharField(max_length=127, blank=True)
    size_bytes = models.PositiveIntegerField(default=0)

    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="uploaded_attachments",
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        """Meta information for the TicketMessageAttachment model."""
        db_table = "ticket_message_attachments"
        ordering = ["created_at"]

    def save(self, *args, **kwargs):
        """Populate metadata automatically from the uploaded file."""
        file = self.file
        if not file:
            super().save(*args, **kwargs)
            return
        if not self.size_bytes:
            self.size_bytes = file.size
        if not self.original_name:
            self.original_name = file.name.split("/")[-1]
        if not self.content_type:
            self.content_type = (
                getattr(file, "content_type", None)
                or getattr(getattr(file, "file", None), "content_type", None) or ""
            )
        super().save(*args, **kwargs)



    def __str__(self):
        """String representation of the TicketMessageAttachment instance."""
        return f"Attachment {self.original_name} for Message {self.message_id}"