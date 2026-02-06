"""
Tests for MyProfileView.

Ensures:
- Anonymous users are redirected to login
- Authenticated users can view their own profile
- Context contains correct profile_user and is_own_profile flag
"""

from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model


class MyProfileViewTests(TestCase):
    """Test suite for the MyProfileView page."""

    def setUp(self):
        """Create a user and common URL for tests."""
        User = get_user_model()
        self.user = User.objects.create_user(
            username="john",
            email="john@example.com",
            password="Pass12345!",
            first_name="John",
            last_name="Doe",
        )
        self.url = reverse("my_profile")

    def login(self):
        """Log in the test user."""
        self.client.login(username="john", password="Pass12345!")

    def test_redirects_when_logged_out(self):
        """Anonymous users should be redirected to login."""
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 302)
        self.assertIn("/login", r["Location"])

    def test_renders_when_logged_in(self):
        """Logged-in users should see their profile and own flag."""
        self.login()
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.context["is_own_profile"])
        self.assertEqual(r.context["profile_user"].pk, self.user.pk)

