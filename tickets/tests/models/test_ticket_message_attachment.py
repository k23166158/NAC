from ast import If
import shutil
import tempfile

from django.test import TestCase, override_settings
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile

from tickets.models import Ticket, TicketMessage
from tickets.models.ticket_message_attachments import TicketMessageAttachment

User = get_user_model()

_TMP_MEDIA = tempfile.mkdtemp()

@override_settings(MEDIA_ROOT=_TMP_MEDIA)
class TicketMessageAttachmentModelTests(TestCase):
    """Tests for the TicketMessageAttachment model."""

    @classmethod
    def tearDownClass(cls):
        """Clean up temporary media files created during tests."""
        shutil.rmtree(_TMP_MEDIA, ignore_errors=True)
        super().tearDownClass()

    def setUp(self):
        """Create a user, ticket, and message used across tests."""
        self.user = User.objects.create_user(
            username="attachuser",
            password="password123",
            email="attach@example.com",
            first_name="Attach",
            last_name="Tester",
        )

        self.ticket = Ticket.objects.create(
            title="Attachment ticket",
            created_by=self.user,
        )

        self.message = TicketMessage.objects.create(
            ticket=self.ticket,
            body="Here is a file",
            sender=self.user,
        )

    def test_attachment_creation_populates_metadata(self):
        """Creating an attachment should populate metadata fields automatically."""
        upload = SimpleUploadedFile(
            "example.txt",
            b"hello world",
            content_type="text/plain",
        )

        att = TicketMessageAttachment.objects.create(
            ticket=self.ticket,
            message=self.message,
            file=upload,
            uploaded_by=self.user,
        )

        self.assertIsNotNone(att.id)
        self.assertEqual(att.ticket, self.ticket)
        self.assertEqual(att.message, self.message)
        self.assertEqual(att.uploaded_by, self.user)

        self.assertEqual(att.original_name, "example.txt")
        self.assertEqual(att.size_bytes, len(b"hello world"))
        self.assertEqual(att.content_type, "text/plain")

    def test_save_with_no_file_early_return_branch(self):
        """Cover the `if not file: return super().save(...)` branch."""
        att = TicketMessageAttachment(
            ticket=self.ticket,
            message=self.message,
            uploaded_by=self.user,
        )
        att.file = None
        att.save()

        self.assertIsNotNone(att.id)

    def test_existing_metadata_is_not_overwritten(self):
        """If metadata is already set, save() should not override it."""
        upload = SimpleUploadedFile(
            "real.pdf",
            b"pdfbytes",
            content_type="application/pdf",
        )

        att = TicketMessageAttachment(
            ticket=self.ticket,
            message=self.message,
            file=upload,
            uploaded_by=self.user,
            original_name="custom.pdf",
            content_type="custom/type",
            size_bytes=999,
        )
        att.save()

        self.assertEqual(att.original_name, "custom.pdf")
        self.assertEqual(att.content_type, "custom/type")
        self.assertEqual(att.size_bytes, 999)

    def test_content_type_not_set_if_file_has_no_content_type(self):
        """If the uploaded file provides no content_type, model should not set it."""
        upload = SimpleUploadedFile(
            "bin.dat",
            b"\x00\x01\x02",
            content_type=None,
        )

        att = TicketMessageAttachment.objects.create(
            ticket=self.ticket,
            message=self.message,
            file=upload,
            uploaded_by=self.user,
        )

        self.assertEqual(att.content_type, "")

    def test_str_representation(self):
        """Test __str__ output includes original name and message id."""
        upload = SimpleUploadedFile("photo.png", b"123", content_type="image/png")

        att = TicketMessageAttachment.objects.create(
            ticket=self.ticket,
            message=self.message,
            file=upload,
            uploaded_by=self.user,
        )

        expected = f"Attachment {att.original_name} for Message {att.message_id}"
        self.assertEqual(str(att), expected)

    def test_message_deletion_cascades(self):
        """Deleting a TicketMessage should delete attachments."""
        upload = SimpleUploadedFile("a.txt", b"abc", content_type="text/plain")

        TicketMessageAttachment.objects.create(
            ticket=self.ticket,
            message=self.message,
            file=upload,
            uploaded_by=self.user,
        )

        self.message.delete()
        self.assertEqual(TicketMessageAttachment.objects.count(), 0)

    def test_ticket_deletion_cascades(self):
        """Deleting a Ticket should delete attachments."""
        upload = SimpleUploadedFile("a.txt", b"abc", content_type="text/plain")

        TicketMessageAttachment.objects.create(
            ticket=self.ticket,
            message=self.message,
            file=upload,
            uploaded_by=self.user,
        )

        self.ticket.delete()
        self.assertEqual(TicketMessageAttachment.objects.count(), 0)

    def test_related_names(self):
        """Test related_name access from Ticket, TicketMessage, and User."""
        upload = SimpleUploadedFile("a.txt", b"abc", content_type="text/plain")

        att = TicketMessageAttachment.objects.create(
            ticket=self.ticket,
            message=self.message,
            file=upload,
            uploaded_by=self.user,
        )

        self.assertIn(att, self.ticket.attachments.all())
        self.assertIn(att, self.message.attachments.all())
        self.assertIn(att, self.user.uploaded_attachments.all())
    
    def test_file_name_keeps_upload_to_path(self):
        """
        If an uploaded filename includes a path, storage should keep upload_to path
        while original_name remains the basename.
        """
        upload = SimpleUploadedFile(
            "folder/subfolder/example.txt",  # IMPORTANT: includes path
            b"hello world",
            content_type="text/plain",
        )

        att = TicketMessageAttachment.objects.create(
            ticket=self.ticket,
            message=self.message,
            file=upload,
            uploaded_by=self.user,
        )

        att.refresh_from_db()
        self.assertEqual(att.original_name, "example.txt")
        self.assertTrue(att.file.name.startswith("ticket_attachments/"))
        self.assertTrue(att.file.name.endswith(".txt"))
        self.assertIn("example", att.file.name)
    
    def test_save_without_file(self):
        """Saving an attachment model without a file attached."""
        att = TicketMessageAttachment(
            ticket=self.ticket,
            message=self.message,
            file=None, # Trigger the 'if not file' branch
            uploaded_by=self.user
        )
        att.save()
        self.assertIsNotNone(att.id)
        self.assertEqual(att.original_name, "")

    def test_second_save_keeps_file_name_stable(self):
        """
        Saving again should preserve the same stored file path.
        """
        upload = SimpleUploadedFile("example.txt", b"hello", content_type="text/plain")

        att = TicketMessageAttachment.objects.create(
            ticket=self.ticket,
            message=self.message,
            file=upload,
            uploaded_by=self.user,
        )

        att.refresh_from_db()
        first_name = att.file.name
        self.assertTrue(first_name.startswith("ticket_attachments/"))
        self.assertTrue(first_name.endswith(".txt"))
        self.assertIn("example", first_name)

        att.save()
        att.refresh_from_db()
        self.assertEqual(att.file.name, first_name)

    def test_create_for_message_helper(self):
        """create_for_message should create attachments for non-null files only."""
        f1 = SimpleUploadedFile("a.txt", b"aaa", content_type="text/plain")
        created = TicketMessageAttachment.create_for_message(
            self.ticket,
            self.message,
            [f1, None],
            self.user,
        )
        self.assertEqual(len(created), 1)
        self.assertEqual(TicketMessageAttachment.objects.filter(message=self.message).count(), 1)
    
    
