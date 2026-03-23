from django.test import TestCase
from django.contrib.auth import get_user_model
from tickets.forms.signup import SignUpForm

User = get_user_model()

class SignUpFormTests(TestCase):
    """Tests for SignUpForm validation and saving."""

    def test_form_valid_and_save(self):
        """Test field exposure, email cleaning, and saving user."""
        f = SignUpForm(data={
            "username": "u", "first_name": "F", "last_name": "L",
            "email": "  E@E.COM  ", "bio": "B",
            "password1": "Pass123!", "password2": "Pass123!"
        })
        expected = {"username", "first_name", "last_name", "email", "profile_picture", "bio", "password1", "password2"}
        self.assertTrue(expected.issubset(set(f.fields.keys())))
        self.assertTrue(f.is_valid())
        user = f.save()
        self.assertEqual(user.username, "u")
        self.assertEqual(user.email, "e@e.com")
        self.assertTrue(user.check_password("Pass123!"))

    def test_duplicate_email_rejected(self):
        """Test that an existing email is rejected."""
        User.objects.create_user(username="ext", email="e@e.com", password="p")
        f = SignUpForm(data={
            "username": "new", "first_name": "F", "last_name": "L",
            "email": "e@e.com", "bio": "B",
            "password1": "Pass123!", "password2": "Pass123!"
        })
        self.assertFalse(f.is_valid())
        self.assertIn("email", f.errors)

    def test_create_active_user_applies_standard_flags(self):
        """create_active_user should create a normal active user."""
        form = SignUpForm(data={
            "username": "newactive",
            "first_name": "F",
            "last_name": "L",
            "email": "  ACTIVE@E.COM ",
            "bio": "B",
            "password1": "Pass123!",
            "password2": "Pass123!",
        })

        self.assertTrue(form.is_valid())
        user = form.create_active_user()

        self.assertTrue(user.is_active)
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertEqual(user.email, "active@e.com")
