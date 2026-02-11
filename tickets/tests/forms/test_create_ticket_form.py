from django.test import TestCase
from django.contrib.auth import get_user_model
from io import BytesIO
from django.core.files.uploadedfile import SimpleUploadedFile

from tickets.forms.ticket_create import CreateTicketForm, MultipleFileInput
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
        self.assertIn("Title cannot be empty.", form.errors["title"])

    def test_whitespace_body_is_invalid(self):
        """Whitespace-only body should fail validation."""
        form = CreateTicketForm(data={
            "title": "Valid title",
            "body": "   ",
            "departments": [self.department.id],
        })
        self.assertFalse(form.is_valid())
        self.assertIn("body", form.errors)
        self.assertIn("Message cannot be empty.", form.errors["body"])

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

    def test_form_accepts_no_attachments(self):
        """Form should be valid with no attachments (optional field)."""
        form = CreateTicketForm(data={
            "title": "Valid title",
            "body": "Valid message",
            "departments": [self.department.id],
        })
        self.assertTrue(form.is_valid())

    def test_form_accepts_single_attachment(self):
        """Form should accept a single file attachment."""
        file = SimpleUploadedFile("test.txt", b"file content", content_type="text/plain")
        form = CreateTicketForm(
            data={
                "title": "Valid title",
                "body": "Valid message",
                "departments": [self.department.id],
            },
            files={"attachments": file},
        )
        self.assertTrue(form.is_valid())

    def test_form_accepts_multiple_attachments(self):
        """Form field is defined and allows multiple files via its widget."""
        form = CreateTicketForm()
        self.assertIn('attachments', form.fields)
        self.assertTrue(form.fields['attachments'].widget.allow_multiple_selected)

    def test_multiple_file_input_widget_allows_multiple(self):
        """MultipleFileInput widget should support multiple file uploads."""
        widget = MultipleFileInput()
        self.assertTrue(widget.allow_multiple_selected)