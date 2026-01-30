from django.test import TestCase
from django.contrib.auth import get_user_model

from tickets.forms.forward_ticket import ForwardTicketForm  # adjust path if needed

User = get_user_model()


class ForwardTicketFormTests(TestCase):
    """Tests for ForwardTicketForm validation + helper methods."""

    def setUp(self):
        """Set up test users."""
        # A valid staff user
        self.staff = User.objects.create_user(
            username="teacher1",
            password="password123",
            email="teacher1@example.com",
            first_name="Teacher",
            last_name="One",
            is_staff=True,
        )

        # A normal (non-staff) user
        self.student = User.objects.create_user(
            username="student1",
            password="password123",
            email="student1@example.com",
            first_name="Student",
            last_name="One",
            is_staff=False,
        )

    def test_form_exposes_email_field_only(self):
        """Form should expose only the email field."""
        form = ForwardTicketForm()
        self.assertIn("email", form.fields)
        self.assertEqual(set(form.fields.keys()), {"email"})

    def test_clean_email_lowercases_and_strips(self):
        """clean_email should strip + lowercase, and accept staff emails."""
        form = ForwardTicketForm(data={"email": "  TEACHER1@EXAMPLE.COM  "})
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data["email"], "teacher1@example.com")

    def test_clean_email_rejects_email_not_found(self):
        """Should reject emails that do not exist in the DB."""
        form = ForwardTicketForm(data={"email": "missing@example.com"})
        self.assertFalse(form.is_valid())
        self.assertIn("email", form.errors)
        self.assertIn("No user found with that email.", form.errors["email"][0])

    def test_clean_email_rejects_non_staff_user(self):
        """Should reject valid users who are not staff."""
        form = ForwardTicketForm(data={"email": "student1@example.com"})
        self.assertFalse(form.is_valid())
        self.assertIn("email", form.errors)
        self.assertIn("That user is not a staff member.", form.errors["email"][0])

    def test_get_user_returns_user_instance_for_valid_staff_email(self):
        """get_user should return the actual User object for a valid email."""
        form = ForwardTicketForm(data={"email": "teacher1@example.com"})
        self.assertTrue(form.is_valid(), form.errors)

        u = form.get_user()
        self.assertEqual(u.id, self.staff.id)
        self.assertEqual(u.email, "teacher1@example.com")
        self.assertTrue(u.is_staff)

    def test_get_user_is_case_insensitive(self):
        """Lookups should be case-insensitive."""
        form = ForwardTicketForm(data={"email": "Teacher1@Example.com"})
        self.assertTrue(form.is_valid(), form.errors)

        u = form.get_user()
        self.assertEqual(u.id, self.staff.id)
