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
        """Create user, ticket, and message for tests."""
        self.user = User.objects.create_user(
            username="u", password="p", email="a@b.com"
        )
        self.ticket = Ticket.objects.create(title="T", created_by=self.user)
        self.message = TicketMessage.objects.create(
            ticket=self.ticket, body="B", sender=self.user
        )

    def test_create_and_save_metadata(self):
        """Test attachment creation, metadata population, and string representation."""
        f1 = SimpleUploadedFile("dir/win\\b.txt", b"abc", content_type="text/plain")
        created = TicketMessageAttachment.create_for_message(
            self.ticket, self.message, [f1, None], self.user
        )
        self.assertEqual(len(created), 1)
        att = created[0]
        self.assertEqual(att.original_name, "b.txt")
        self.assertEqual(att.content_type, "text/plain")
        self.assertEqual(att.size_bytes, 3)
        self.assertIn("b.txt", str(att))

    def test_save_existing_and_no_file(self):
        """Test saving with no file or with pre-existing metadata."""
        att1 = TicketMessageAttachment(ticket=self.ticket, message=self.message)
        att1.save()
        self.assertIsNotNone(att1.id)
        f2 = SimpleUploadedFile("x.pdf", b"p", content_type="application/pdf")
        att2 = TicketMessageAttachment(
            ticket=self.ticket, message=self.message, file=f2,
            original_name="y.pdf", content_type="c", size_bytes=99
        )
        att2.save()
        self.assertEqual(att2.original_name, "y.pdf")
        self.assertEqual(att2.content_type, "c")
        self.assertEqual(att2.size_bytes, 99)

    def test_delete_attachments(self):
        """Test deleting attachments with and without files."""
        f = SimpleUploadedFile("x.txt", b"x", content_type="text/plain")
        a1 = TicketMessageAttachment.objects.create(
            ticket=self.ticket, message=self.message, file=f
        )
        a2 = TicketMessageAttachment.objects.create(
            ticket=self.ticket, message=self.message
        )
        empty_deleted = TicketMessageAttachment.delete_for_message(self.message, [])
        self.assertEqual(empty_deleted, 0)
        deleted = TicketMessageAttachment.delete_for_message(
            self.message, [str(a1.id), str(a2.id)]
        )
        self.assertEqual(deleted, 2)
        self.assertEqual(TicketMessageAttachment.objects.count(), 0)

    def test_edge_cases_and_fallbacks(self):
        """Test fallbacks for missing content_type, size, and name."""
        f = SimpleUploadedFile("f.dat", b"d", content_type=None)
        att = TicketMessageAttachment.objects.create(
            ticket=self.ticket, message=self.message, file=f
        )
        self.assertEqual(att.content_type, "")
        f.file = type("Mock", (), {"content_type": "nested/type"})()
        f.content_type = None
        self.assertEqual(att._content_type_from(f), "nested/type")
        f.name = None
        self.assertEqual(att._basename(f), "")
        f.size = None
        att.size_bytes = 0
        att._ensure_size(f)
        self.assertEqual(att.size_bytes, 0)