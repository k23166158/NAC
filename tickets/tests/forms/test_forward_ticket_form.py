from django.test import TestCase
from django.contrib.auth import get_user_model
from types import SimpleNamespace
from tickets.forms.forward_ticket import ForwardTicketForm
from tickets.views.forward_ticket_view import _ticket_redirect, _err, _has_field

class ForwardTicketFormTests(TestCase):
    """Tests for ForwardTicketForm and helpers."""

    def setUp(self):
        """Set up test users."""
        User = get_user_model()
        self.staff = User.objects.create_user(username="t", email="t@e.com", password="p", is_staff=True)
        self.student = User.objects.create_user(username="s", email="s@e.com", password="p", is_staff=False)

    def test_form_valid_and_fields(self):
        """Test exposed fields, clean email, and get_user."""
        f = ForwardTicketForm(data={"email": "  T@E.COM  "})
        self.assertEqual(set(f.fields.keys()), {"email"})
        self.assertTrue(f.is_valid())
        self.assertEqual(f.cleaned_data["email"], "t@e.com")
        self.assertEqual(f.get_user().id, self.staff.id)

    def test_form_invalid_emails(self):
        """Test form rejects non-existent and non-staff emails."""
        f1 = ForwardTicketForm(data={"email": "missing@e.com"})
        self.assertFalse(f1.is_valid())
        self.assertIn("email", f1.errors)
        f2 = ForwardTicketForm(data={"email": "s@e.com"})
        self.assertFalse(f2.is_valid())
        self.assertIn("email", f2.errors)

    def test_helpers(self):
        """Test view helpers."""
        resp = _ticket_redirect("active", "abc-123")
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/?tab=active&open=abc-123", resp["Location"])
        self.assertEqual(_err(SimpleNamespace(errors={})), "Email failed to forward.")
        Dummy = SimpleNamespace(_meta=SimpleNamespace(fields=[SimpleNamespace(name="foo")]))
        self.assertFalse(_has_field(Dummy, "missing"))