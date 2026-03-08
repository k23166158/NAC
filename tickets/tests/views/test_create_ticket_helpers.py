from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile

from tickets.models import Ticket, TicketMessage, TicketAssigned, Department, TicketMessageAttachment


User = get_user_model()


class CreateAttachmentsTests(TestCase):
    """Tests for the TicketMessageAttachment.create_for_message model helper."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="pass12345",
        )
        creator = User.objects.create_user(
            username="creator",
            email="creator@example.com",
            password="pass12345",
        )
        self.ticket = Ticket.objects.create(
            title="Test Ticket",
            created_by=self.user,
        )
        self.message = TicketMessage.objects.create(
            ticket=self.ticket,
            sender=self.user,
            body="Test message",
        )

    def test_create_attachments_with_none_files(self):
        """Test that create_for_message handles None files gracefully."""
        TicketMessageAttachment.create_for_message(
            self.ticket,
            self.message,
            None,
            self.user,
        )
        self.assertEqual(TicketMessageAttachment.objects.count(), 0)

    def test_create_attachments_with_empty_list(self):
        """Test that create_for_message handles empty file list gracefully."""
        TicketMessageAttachment.create_for_message(
            self.ticket,
            self.message,
            [],
            self.user,
        )
        self.assertEqual(TicketMessageAttachment.objects.count(), 0)

    def test_create_attachments_with_single_file(self):
        """Test creating attachment with a single file."""
        file = SimpleUploadedFile("test.txt", b"content", content_type="text/plain")
        TicketMessageAttachment.create_for_message(
            self.ticket,
            self.message,
            [file],
            self.user,
        )
        
        self.assertEqual(TicketMessageAttachment.objects.count(), 1)
        attachment = TicketMessageAttachment.objects.first()
        self.assertEqual(attachment.ticket, self.ticket)
        self.assertEqual(attachment.message, self.message)
        self.assertEqual(attachment.original_name, "test.txt")
        self.assertEqual(attachment.content_type, "text/plain")
        self.assertEqual(attachment.uploaded_by, self.user)

    def test_create_attachments_with_multiple_files(self):
        """Test creating attachments with multiple files."""
        files = [
            SimpleUploadedFile("test1.txt", b"content1", content_type="text/plain"),
            SimpleUploadedFile("test2.pdf", b"content2", content_type="application/pdf"),
        ]
        TicketMessageAttachment.create_for_message(
            self.ticket,
            self.message,
            files,
            self.user,
        )
        
        self.assertEqual(TicketMessageAttachment.objects.count(), 2)

    def test_create_attachments_with_missing_content_type(self):
        """Test creating attachment when content_type is not provided."""
        file = SimpleUploadedFile("test.bin", b"binary content")
        file.content_type = None
        TicketMessageAttachment.create_for_message(
            self.ticket,
            self.message,
            [file],
            self.user,
        )
        
        attachment = TicketMessageAttachment.objects.first()
        self.assertEqual(attachment.content_type, "")

    def test_create_attachments_stores_file_size(self):
        """Test that file size is correctly stored."""
        content = b"test content"
        file = SimpleUploadedFile("test.txt", content, content_type="text/plain")
        TicketMessageAttachment.create_for_message(
            self.ticket,
            self.message,
            [file],
            self.user,
        )
        
        attachment = TicketMessageAttachment.objects.first()
        self.assertEqual(attachment.size_bytes, len(content))

    def test_create_attachments_with_none_file_in_list(self):
        """Test that None values in file list are skipped."""
        files = [
            SimpleUploadedFile("test.txt", b"content", content_type="text/plain"),
            None,
        ]
        TicketMessageAttachment.create_for_message(
            self.ticket,
            self.message,
            files,
            self.user,
        )
        
        self.assertEqual(TicketMessageAttachment.objects.count(), 1)

    def test_create_attachments_with_all_none_files(self):
        """Test that empty attachments list is handled when all files are None."""
        files = [None, None]
        TicketMessageAttachment.create_for_message(
            self.ticket,
            self.message,
            files,
            self.user,
        )
        
        self.assertEqual(TicketMessageAttachment.objects.count(), 0)


class CreateTicketObjectsTests(TestCase):
    """Tests for Ticket.create_with_initial_message model helper."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="pass12345",
        )
        creator = User.objects.create_user(
            username="creator",
            email="creator@example.com",
            password="pass12345",
        )
        self.dept1 = Department.objects.create(name="Support", created_by=creator)
        self.dept2 = Department.objects.create(name="Billing", created_by=creator)

    def test_create_ticket_objects_without_files(self):
        """Test creating ticket objects without attachments."""
        cleaned_data = {
            "title": "Test Ticket",
            "body": "Test body",
            "departments": [self.dept1],
        }
        ticket = Ticket.create_with_initial_message(
            creator=self.user,
            cleaned_data=cleaned_data,
            files=None,
        )
        
        self.assertIsNotNone(ticket)
        self.assertEqual(ticket.title, "Test Ticket")
        self.assertEqual(ticket.created_by, self.user)
        self.assertEqual(TicketMessage.objects.count(), 1)
        self.assertEqual(TicketAssigned.objects.count(), 1)
        self.assertEqual(TicketMessageAttachment.objects.count(), 0)

    def test_create_ticket_objects_with_files(self):
        """Test creating ticket objects with attachments."""
        files = [
            SimpleUploadedFile("test.txt", b"content", content_type="text/plain"),
        ]
        cleaned_data = {
            "title": "Test Ticket",
            "body": "Test body",
            "departments": [self.dept1],
        }
        ticket = Ticket.create_with_initial_message(
            creator=self.user,
            cleaned_data=cleaned_data,
            files=files,
        )
        
        self.assertIsNotNone(ticket)
        self.assertEqual(TicketMessageAttachment.objects.count(), 1)

    def test_create_ticket_objects_with_multiple_departments(self):
        """Test creating ticket objects assigned to multiple departments."""
        cleaned_data = {
            "title": "Test Ticket",
            "body": "Test body",
            "departments": [self.dept1, self.dept2],
        }
        ticket = Ticket.create_with_initial_message(
            creator=self.user,
            cleaned_data=cleaned_data,
            files=None,
        )
        
        self.assertEqual(TicketAssigned.objects.count(), 2)
        departments = [
            assignment.department for assignment in
            TicketAssigned.objects.filter(ticket=ticket)
        ]
        self.assertIn(self.dept1, departments)
        self.assertIn(self.dept2, departments)

    def test_create_ticket_objects_atomicity(self):
        """Test that ticket creation is atomic."""
        cleaned_data = {
            "title": "Test Ticket",
            "body": "Test body",
            "departments": [self.dept1],
        }
        ticket = Ticket.create_with_initial_message(
            creator=self.user,
            cleaned_data=cleaned_data,
            files=None,
        )
        
        # Verify all related objects were created
        self.assertEqual(Ticket.objects.filter(id=ticket.id).count(), 1)
        self.assertEqual(
            TicketMessage.objects.filter(ticket=ticket).count(),
            1
        )
        self.assertEqual(
            TicketAssigned.objects.filter(ticket=ticket).count(),
            1
        )

    def test_create_ticket_objects_message_sender_is_creator(self):
        """Test that the initial message sender is the ticket creator."""
        cleaned_data = {
            "title": "Test Ticket",
            "body": "Test body",
            "departments": [self.dept1],
        }
        ticket = Ticket.create_with_initial_message(
            creator=self.user,
            cleaned_data=cleaned_data,
            files=None,
        )
        
        message = TicketMessage.objects.get(ticket=ticket)
        self.assertEqual(message.sender, self.user)


class BuildAssignmentsTests(TestCase):
    """Tests for the TicketAssigned.build_for_departments model helper."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="pass12345",
        )
        creator = User.objects.create_user(
            username="creator",
            email="creator@example.com",
            password="pass12345",
        )
        self.ticket = Ticket.objects.create(
            title="Test Ticket",
            created_by=self.user,
        )
        self.dept1 = Department.objects.create(name="Support", created_by=creator)
        self.dept2 = Department.objects.create(name="Billing", created_by=creator)

    def test_build_assignments_single_department(self):
        """Test building assignment for a single department."""
        assignments = TicketAssigned.build_for_departments(self.ticket, [self.dept1])
        
        self.assertEqual(len(assignments), 1)
        self.assertEqual(assignments[0].ticket, self.ticket)
        self.assertEqual(assignments[0].department, self.dept1)

    def test_build_assignments_multiple_departments(self):
        """Test building assignments for multiple departments."""
        assignments = TicketAssigned.build_for_departments(
            self.ticket,
            [self.dept1, self.dept2]
        )
        
        self.assertEqual(len(assignments), 2)
        departments = [a.department for a in assignments]
        self.assertIn(self.dept1, departments)
        self.assertIn(self.dept2, departments)

    def test_build_assignments_empty_departments(self):
        """Test building assignments with empty department list."""
        assignments = TicketAssigned.build_for_departments(self.ticket, [])
        
        self.assertEqual(len(assignments), 0)
