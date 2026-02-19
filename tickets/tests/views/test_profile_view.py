"""
Tests for ProfileView (slug-based).

Covers:
- Redirects anonymous users to login
- Loads another user's profile
- Loads own profile and sets is_own_profile True
- Returns 404 for unknown slugs
"""

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse


class ProfileViewTests(TestCase):
    """Tests for viewing profiles via /profile/<profile_slug>/."""

    def setUp(self):
        """Create users and ensure slugs exist."""
        User = get_user_model()
        self.user = User.objects.create_user(
            username="john.doe",
            email="john@example.com",
            password="Pass12345!",
            first_name="John",
            last_name="Doe",
        )
        self.other = User.objects.create_user(
            username="jane_roe",
            email="jane@example.com",
            password="Pass12345!",
            first_name="Jane",
            last_name="Roe",
        )
        self.user.refresh_from_db()
        self.other.refresh_from_db()

    def login(self):
        """Force login for reliability."""
        self.client.force_login(self.user)

    def test_redirects_when_logged_out(self):
        """Anonymous users should be redirected to login."""
        url = reverse("profile", kwargs={"profile_slug": self.other.profile_slug})
        r = self.client.get(url)
        self.assertEqual(r.status_code, 302)
        self.assertIn("/login", r["Location"])

    def test_views_other_user_sets_flag_false(self):
        """Viewing another user sets is_own_profile False."""
        self.login()
        url = reverse("profile", kwargs={"profile_slug": self.other.profile_slug})
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)
        self.assertFalse(r.context["is_own_profile"])
        self.assertEqual(r.context["profile_user"].pk, self.other.pk)

    def test_views_self_sets_flag_true(self):
        """Viewing own slug sets is_own_profile True."""
        self.login()
        url = reverse("profile", kwargs={"profile_slug": self.user.profile_slug})
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.context["is_own_profile"])
        self.assertEqual(r.context["profile_user"].pk, self.user.pk)

    def test_unknown_slug_returns_404(self):
        """Unknown slugs should return a 404."""
        self.login()
        url = reverse("profile", kwargs={"profile_slug": "no-such-user"})
        r = self.client.get(url)
        self.assertEqual(r.status_code, 404)