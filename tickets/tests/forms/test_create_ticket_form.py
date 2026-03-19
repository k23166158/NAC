from django.test import TestCase
from django.contrib.auth import get_user_model
from io import BytesIO
from django.core.files.uploadedfile import SimpleUploadedFile

from tickets.forms.ticket_create import CreateTicketForm
from tickets.models import Department

class CreateTicketFormTests(TestCase):
    """Tests for CreateTicketForm validation branches."""
    def setUp(self):
        """Setup dependencies for ticket creation tests."""
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
        """Ensure ticket title cannot be only whitespace."""
        form = CreateTicketForm(data={"title": "   ", "body": "Valid", "departments": [self.department.id]})
        self.assertFalse(form.is_valid())
        self.assertIn("Title cannot be empty.", form.errors["title"])

    def test_whitespace_body_is_invalid(self):
        """Ensure ticket body cannot be only whitespace."""
        form = CreateTicketForm(data={"title": "Valid", "body": "   ", "departments": [self.department.id]})
        self.assertFalse(form.is_valid())
        self.assertIn("Message cannot be empty.", form.errors["body"])

    def test_title_and_body_are_stripped_when_valid(self):
        """Ensure leading and trailing whitespaces are stripped from valid inputs."""
        form = CreateTicketForm(data={"title": "  Need help  ", "body": "  Hello  ", "departments": [self.department.id]})
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data["title"], "Need help")
        self.assertEqual(form.cleaned_data["body"], "Hello")

    def test_form_accepts_optional_or_single_attachment(self):
        """Form should be valid with no attachments or a single attachment."""
        form_no_file = CreateTicketForm(data={"title": "Valid", "body": "Valid", "departments": [self.department.id]})
        self.assertTrue(form_no_file.is_valid())

        file = SimpleUploadedFile("test.txt", b"file content", content_type="text/plain")
        form_with_file = CreateTicketForm(
            data={"title": "Valid", "body": "Valid", "departments": [self.department.id]},
            files={"attachments": file},
        )
        self.assertTrue(form_with_file.is_valid())

    def test_more_than_three_departments_is_invalid(self):
        """Ensure selecting more than 3 departments is rejected."""
        User = get_user_model()
        creator = User.objects.first()
        depts = [self.department]
        for i in range(3):
            depts.append(Department.objects.create(name=f"Dept{i}", created_by=creator))
        form = CreateTicketForm(data={
            "title": "Valid",
            "body": "Valid",
            "departments": [d.id for d in depts],
        })
        self.assertFalse(form.is_valid())
        self.assertIn("You can select at most 3 departments.", form.errors["departments"])

    def test_three_departments_is_valid(self):
        """Ensure selecting exactly 3 departments is accepted."""
        User = get_user_model()
        creator = User.objects.first()
        depts = [self.department]
        for i in range(2):
            depts.append(Department.objects.create(name=f"Dept{i}", created_by=creator))
        form = CreateTicketForm(data={
            "title": "Valid",
            "body": "Valid",
            "departments": [d.id for d in depts],
        })
        self.assertTrue(form.is_valid())

    def test_form_accepts_multiple_attachments(self):
        """Form field is defined and allows multiple files via its widget."""
        form = CreateTicketForm()
        self.assertIn('attachments', form.fields)
        self.assertTrue(form.fields['attachments'].widget.allow_multiple_selected)