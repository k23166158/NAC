from django.test import TestCase
from django.contrib.auth import get_user_model
from tickets.forms.signup import SignUpForm

User = get_user_model()


class SignUpFormTests(TestCase):
    """Tests for SignUpForm validation and field configuration."""

    def test_form_exposes_expected_fields(self):
        """Form should expose the intended fields and password fields."""
        form = SignUpForm()
        expected = {
            "username", "first_name", "last_name", "email",
            "profile_picture", "bio", "password1", "password2"
        }
        self.assertTrue(expected.issubset(set(form.fields.keys())))

    def test_clean_email_lowercases_and_strips(self):
        """clean_email should lowercase and strip whitespace."""
        form = SignUpForm(data={
            "username": "u1",
            "first_name": "A",
            "last_name": "B",
            "email": "  TEST@EXAMPLE.COM  ",
            "bio": "",
            "password1": "StrongPass123!!",
            "password2": "StrongPass123!!",
        })
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data["email"], "test@example.com")

    def test_clean_email_rejects_duplicate_email(self):
        """clean_email should reject an email already in use."""
        User.objects.create_user(
            username="existing",
            password="StrongPass123!!",
            first_name="X",
            last_name="Y",
            email="dup@example.com",
        )

        form = SignUpForm(data={
            "username": "newuser",
            "first_name": "A",
            "last_name": "B",
            "email": "dup@example.com",
            "bio": "",
            "password1": "StrongPass123!!",
            "password2": "StrongPass123!!",
        })
        self.assertFalse(form.is_valid())
        self.assertIn("email", form.errors)

    def test_form_saves_user_with_required_fields(self):
        """Valid form should save a user record (without files)."""
        form = SignUpForm(data={
            "username": "saveduser",
            "first_name": "Save",
            "last_name": "User",
            "email": "saveduser@example.com",
            "bio": "Hello",
            "password1": "StrongPass123!!",
            "password2": "StrongPass123!!",
        })
        self.assertTrue(form.is_valid(), form.errors)
        user = form.save()
        self.assertEqual(user.username, "saveduser")
        self.assertEqual(user.email, "saveduser@example.com")
        self.assertTrue(user.check_password("StrongPass123!!"))
