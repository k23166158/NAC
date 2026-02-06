"""
Tests for ProfileView.

Ensures:
- Anonymous users are redirected to login
- Authenticated users can view other profiles
- Context includes correct profile_user and is_own_profile flag
"""

from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model


class ProfileViewTests(TestCase):
    """Test suite for viewing user profiles via ProfileView."""

    def setUp(self):
        """Create two users and prepare URLs."""
        User = get_user_model()
        self.user = User.objects.create_user(
            username="john",
            email="john@example.com",
            password="Pass12345!",
            first_name="John",
            last_name="Doe",
        )
        self.other = User.objects.create_user(
            username="jane",
            email="jane@example.com",
            password="Pass12345!",
            first_name="Jane",
            last_name="Roe",
        )
        self.other_url = reverse("profile", kwargs={"pk": self.other.pk})
        self.self_url = reverse("profile", kwargs={"pk": self.user.pk})
        self.my_url = reverse("my_profile")

    def login(self):
        """Log in the primary user."""
        self.client.login(username="john", password="Pass12345!")

    def test_redirects_when_logged_out(self):
        """Anonymous users should be redirected to login."""
        r = self.client.get(self.other_url)
        self.assertEqual(r.status_code, 302)
        self.assertIn("/login", r["Location"])

    def test_views_other_user_sets_flag_false(self):
        """Viewing another user should set is_own_profile False."""
        self.login()
        r = self.client.get(self.other_url)
        self.assertEqual(r.status_code, 200)
        self.assertFalse(r.context["is_own_profile"])
        self.assertEqual(r.context["profile_user"].pk, self.other.pk)

    def test_views_self_redirects_to_my_profile(self):
        """Viewing own pk through ProfileView should redirect to my_profile."""
        self.login()
        r = self.client.get(self.self_url)
        self.assertEqual(r.status_code, 302)
        self.assertEqual(r["Location"], self.my_url)
