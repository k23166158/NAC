# tickets/tests/views/test_create_ticket_view.py
from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model

from tickets.models import Department, Ticket, TicketMessage, TicketAssigned


class CreateTicketViewTests(TestCase):
    def setUp(self):
        """Set up users and a department for testing."""
        User = get_user_model()
        self.student = User.objects.create_user(
            username="student1",
            email="student1@example.com",
            first_name="John",
            last_name="Doe",
            password="pass12345",
        )
        self.creator = User.objects.create_user(
            username="creator1",
            email="creator1@example.com",
            first_name="Jane",
            last_name="Doe",
            password="pass12345",
        )
        self.department = Department.objects.create(name="Support", created_by=self.creator)

    def test_get_requires_login(self):
        """Test that GET request redirects to login if user is not authenticated."""
        url = reverse("ticket_create")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        self.assertIn("login", response.url)

    def test_get_renders_template_when_logged_in(self):
        """Test that GET request renders the create ticket template for logged-in users."""
        self.client.login(username="student1", password="pass12345")
        response = self.client.get(reverse("ticket_create"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "create_ticket.html")
        self.assertIn("form", response.context)

    def test_post_invalid_shows_errors(self):
        """Test that POST request with invalid data re-renders the form with errors."""
        self.client.login(username="student1", password="pass12345")
        response = self.client.post(
            reverse("ticket_create"),
            data={"title": "", "department": self.department.id, "body": ""},
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "create_ticket.html")
        self.assertEqual(Ticket.objects.count(), 0)
        self.assertEqual(TicketMessage.objects.count(), 0)
        self.assertEqual(TicketAssigned.objects.count(), 0)

    def test_post_valid_creates_ticket_message_and_assignment(self):
        """Test that POST request with valid data creates Ticket, TicketMessage, and TicketAssigned."""
        self.client.login(username="student1", password="pass12345")
        response = self.client.post(
            reverse("ticket_create"),
            data={
                "title": "Need help",
                "department": self.department.id,
                "body": "I need support with my module.",
            },
        )
        self.assertEqual(response.status_code, 302)

        self.assertEqual(Ticket.objects.count(), 1)
        self.assertEqual(TicketMessage.objects.count(), 1)
        self.assertEqual(TicketAssigned.objects.count(), 1)

        ticket = Ticket.objects.first()
        self.assertEqual(ticket.title, "Need help")
        self.assertEqual(ticket.created_by, self.student)

        msg = TicketMessage.objects.first()
        self.assertEqual(msg.ticket, ticket)
        self.assertEqual(msg.sender, self.student)
        self.assertEqual(msg.body, "I need support with my module.")

        assignment = TicketAssigned.objects.first()
        self.assertEqual(assignment.ticket, ticket)
        self.assertEqual(assignment.department, self.department)