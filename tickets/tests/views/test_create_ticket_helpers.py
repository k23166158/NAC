from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from tickets.models import Ticket, TicketMessage, TicketAssigned, Department, TicketMessageAttachment

User = get_user_model()

class TicketCreateHelpersTests(TestCase):
    """Tests for the Ticket Creation."""

    def setUp(self):
        """Set up the test users, department and tickets/messages"""
        self.user = User.objects.create_user(username="testuser", email="t@example.com", password="pwd")
        self.dept1 = Department.objects.create(name="Support", created_by=self.user)
        self.dept2 = Department.objects.create(name="Billing", created_by=self.user)
        self.ticket = Ticket.objects.create(title="Ticket", created_by=self.user)
        self.message = TicketMessage.objects.create(ticket=self.ticket, sender=self.user, body="Body")

    def test_create_attachments_comprehensive(self):
        """Test adding ticket attachments"""
        file1 = SimpleUploadedFile("test1.txt", b"content1", content_type="text/plain")
        file2 = SimpleUploadedFile("test2.bin", b"binary")
        file2.content_type = None
        
        TicketMessageAttachment.create_for_message(self.ticket, self.message, [file1, file2, None], self.user)
        TicketMessageAttachment.create_for_message(self.ticket, self.message, None, self.user)
        
        self.assertEqual(TicketMessageAttachment.objects.count(), 2)
        
        # Query explicitly by original_name to remove flakiness over insertion order
        att1 = TicketMessageAttachment.objects.get(original_name="test1.txt")
        self.assertEqual(att1.content_type, "text/plain")
        self.assertEqual(att1.size_bytes, 8)
        
        att2 = TicketMessageAttachment.objects.get(original_name="test2.bin")
        self.assertEqual(att2.content_type, "")

    def test_create_ticket_objects_and_assignments(self):
        """Test creating ticket attachments and assigning them to tickets"""
        file = SimpleUploadedFile("test.txt", b"content", content_type="text/plain")
        data = {"title": "T1", "body": "B1", "departments": [self.dept1, self.dept2]}
        
        ticket = Ticket.create_with_initial_message(creator=self.user, cleaned_data=data, files=[file])
        
        self.assertEqual(ticket.title, "T1")
        self.assertEqual(TicketMessage.objects.get(ticket=ticket).sender, self.user)
        self.assertEqual(TicketAssigned.objects.filter(ticket=ticket).count(), 2)
        self.assertEqual(TicketMessageAttachment.objects.filter(ticket=ticket).count(), 1)
        
        self.assertEqual(len(TicketAssigned.build_for_departments(self.ticket, [])), 0)
