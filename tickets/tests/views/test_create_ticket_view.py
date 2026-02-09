from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model

from tickets.models import Department, Ticket, TicketMessage, TicketAssigned


class CreateTicketViewTests(TestCase):
    """Tests for the CreateTicketView to ensure correct ticket creation and form handling."""
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

    def _login_student(self):
        """Log in the student user."""
        self.client.login(username="student1", password="pass12345")

    def _post_valid(self):
        """Post valid create-ticket data."""
        return self.client.post(
            reverse("ticket_create"),
            data={
                "title": "Need help",
                "departments": [self.department.id],
                "body": "I need support with my module.",
            },
        )

    def _assert_created_counts(self, tickets=1, messages=1, assigned=1):
        """Assert expected object counts after creation."""
        self.assertEqual(Ticket.objects.count(), tickets)
        self.assertEqual(TicketMessage.objects.count(), messages)
        self.assertEqual(TicketAssigned.objects.count(), assigned)

    def _assert_ticket_details(self, ticket):
        """Assert created ticket fields."""
        self.assertEqual(ticket.title, "Need help")
        self.assertEqual(ticket.created_by, self.student)

    def _assert_message_details(self, msg, ticket):
        """Assert created first message fields."""
        self.assertEqual(msg.ticket, ticket)
        self.assertEqual(msg.sender, self.student)
        self.assertEqual(msg.body, "I need support with my module.")

    def _assert_assignment_details(self, assignment, ticket):
        """Assert created assignment fields."""
        self.assertEqual(assignment.ticket, ticket)
        self.assertEqual(assignment.department, self.department)

    def test_get_requires_login(self):
        """Test that GET request redirects to login if user is not authenticated."""
        response = self.client.get(reverse("ticket_create"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("login", response.url)

    def test_get_renders_template_when_logged_in(self):
        """Test that GET request renders the create ticket template for logged-in users."""
        self._login_student()
        response = self.client.get(reverse("ticket_create"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "create_ticket.html")
        self.assertIn("form", response.context)

    def test_post_invalid_shows_errors(self):
        """Test that POST request with invalid data re-renders the form with errors."""
        self._login_student()
        response = self.client.post(
            reverse("ticket_create"),
            data={"title": "", "departments": [self.department.id], "body": ""},
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "create_ticket.html")
        self._assert_created_counts(tickets=0, messages=0, assigned=0)

    def test_post_valid_creates_ticket_message_and_assignment(self):
        """Test that POST request with valid data creates Ticket, TicketMessage, and TicketAssigned."""
        self._login_student()
        response = self._post_valid()
        self.assertEqual(response.status_code, 302)

        self._assert_created_counts()
        ticket = Ticket.objects.first()
        msg = TicketMessage.objects.first()
        assignment = TicketAssigned.objects.first()

        self._assert_ticket_details(ticket)
        self._assert_message_details(msg, ticket)
        self._assert_assignment_details(assignment, ticket)