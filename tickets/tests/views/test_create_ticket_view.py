from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile

from tickets.models import Department, Ticket, TicketMessage, TicketAssigned, TicketMessageAttachment
from tickets.views.ticket_create import create_attachments

class CreateTicketViewTests(TestCase):
    """Tests for the CreateTicketView handling."""

    def setUp(self):
        """Set up users and a department."""
        User = get_user_model()
        self.s = User.objects.create_user(username="s", password="p")
        self.d = Department.objects.create(name="Support", created_by=self.s)
        self.url = reverse("ticket_create")

    def test_get_access_and_render(self):
        """Test auth requirement and template rendering for GET."""
        res1 = self.client.get(self.url)
        self.assertEqual(res1.status_code, 302)
        self.client.login(username="s", password="p")
        res2 = self.client.get(self.url)
        self.assertEqual(res2.status_code, 200)
        self.assertTemplateUsed(res2, "create_ticket.html")

    def test_post_invalid_shows_errors(self):
        """Test POST with invalid data."""
        self.client.login(username="s", password="p")
        res = self.client.post(self.url, data={"title": "", "departments": [self.d.id], "body": ""})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(Ticket.objects.count(), 0)

    def test_post_valid_creates_ticket_and_attachments(self):
        """Test POST with valid data and files creates records."""
        self.client.login(username="s", password="p")
        f = SimpleUploadedFile("t.txt", b"c", content_type="text/plain")
        res = self.client.post(self.url, data={
            "title": "H", "departments": [self.d.id], "body": "B"
        }, files={"attachments": f})
        self.assertEqual(res.status_code, 302)
        self.assertEqual(Ticket.objects.count(), 1)
        self.assertEqual(TicketMessage.objects.count(), 1)
        self.assertEqual(TicketAssigned.objects.count(), 1)
        t = Ticket.objects.first()
        self.assertEqual(t.title, "H")
        self.assertEqual(t.created_by, self.s)

    def test_create_attachments_skips_when_no_valid_files(self):
        """create_attachments should early-return when there are no truthy file objects."""
        # Build a ticket and initial message
        t = Ticket.objects.create(title="No files", created_by=self.s)
        msg = TicketMessage.objects.create(ticket=t, sender=self.s, body="Body")

        # Pass a list containing only falsy entries; attachments list should be empty
        create_attachments(t, msg, files=[None, None], user=self.s)

        self.assertEqual(TicketMessageAttachment.objects.count(), 0)