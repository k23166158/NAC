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

    @classmethod
    def create_for_message(cls, ticket, message, files, user):
        """Persist uploaded files for a ticket message."""
        created = []
        for file in filter(None, files or []):
            created.append(
                cls.objects.create(
                    ticket=ticket,
                    message=message,
                    file=file,
                    uploaded_by=user,
                )
            )
        return created

    @classmethod
    def delete_for_message(cls, message, attachment_ids):
        """Delete selected attachments belonging to a message."""
        if not attachment_ids:
            return 0
        queryset = cls.objects.filter(message=message, id__in=attachment_ids)
        deleted = 0
        for attachment in queryset:
            # Remove the backing file from storage when possible.
            if attachment.file:
                attachment.file.delete(save=False)
            attachment.delete()
            deleted += 1
        return deleted

    def save(self, *args, **kwargs):
        """Populate metadata automatically from the uploaded file."""
        file = self.file
        if not file:
            return super().save(*args, **kwargs)
        basename = self._basename(file)
        self._ensure_size(file)
        if not self.original_name:
            self.original_name = basename
        if not self.content_type:
            self.content_type = self._content_type_from(file)
        super().save(*args, **kwargs)

    def _basename(self, file):
        """Extract the base filename from the file or its name attribute."""
        name = getattr(file, "name", "") or ""
        return name.split("/")[-1].split("\\")[-1]

    def _ensure_size(self, file):
        """Ensure size_bytes is populated from file if not already set."""
        if not self.size_bytes:
            self.size_bytes = getattr(file, "size", 0) or 0

    def _content_type_from(self, file):
        """Try to get content type from file or its file attribute, default to empty string."""
        return (
            getattr(file, "content_type", None)
            or getattr(getattr(file, "file", None), "content_type", None)
            or ""
        )

    def __str__(self):
        """String representation of the TicketMessageAttachment instance."""
        return f"Attachment {self.original_name} for Message {self.message_id}"
