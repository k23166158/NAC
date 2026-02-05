from django.test import TestCase
from django.contrib.auth import get_user_model

from tickets.forms.ticket_create import CreateTicketForm
from tickets.models import Department


class CreateTicketFormTests(TestCase):
    """Tests for CreateTicketForm validation branches."""
    def setUp(self):
        """Create a department to select in the form."""
        User = get_user_model()
        creator = User.objects.create_user(
            username="creator",
            email="creator@example.com",
            first_name="Creator",
            last_name="User",
            password="pass12345",
        )
        self.department = Department.objects.create(name="Support", created_by=creator)

    def test_whitespace_title_is_invalid(self):
        """Whitespace-only title should fail validation."""
        form = CreateTicketForm(data={
            "title": "   ",
            "body": "Valid message",
            "departments": [self.department.id],
        })
        self.assertFalse(form.is_valid())
        self.assertIn("title", form.errors)

    def test_whitespace_body_is_invalid(self):
        """Whitespace-only body should fail validation."""
        form = CreateTicketForm(data={
            "title": "Valid title",
            "body": "   ",
            "departments": [self.department.id],
        })
        self.assertFalse(form.is_valid())
        self.assertIn("body", form.errors)

    def test_title_and_body_are_stripped_when_valid(self):
        """Valid data is accepted and whitespace is stripped."""
        form = CreateTicketForm(data={
            "title": "  Need help  ",
            "body": "  Hello there  ",
            "departments": [self.department.id],
        })
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data["title"], "Need help")
        self.assertEqual(form.cleaned_data["body"], "Hello there")