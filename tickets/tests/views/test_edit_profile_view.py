"""
Tests for EditProfileView.

Ensures:
- Anonymous users are redirected to login
- GET renders for authenticated users
- POST updates profile fields2
- POST updates password when provided
- POST saves profile picture upload
"""

import tempfile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.auth import get_user_model


@override_settings(MEDIA_ROOT=tempfile.gettempdir())
class EditProfileViewTests(TestCase):
    """Test suite for editing a user's profile via ProfileEditView."""

    def setUp(self):
        """Create a user and edit URL."""
        User = get_user_model()
        self.user = User.objects.create_user(
            username="john",
            email="john@example.com",
            password="Pass12345!",
            first_name="John",
            last_name="Doe",
        )
        self.url = reverse("profile_edit")

    def login(self):
        """Log in the test user."""
        self.client.login(username="john", password="Pass12345!")

    def base_payload(self):
        """Return a minimal valid payload for editing profile."""
        return {
            "first_name": "John",
            "last_name": "Doe",
            "username": "john",
            "email": "john@example.com",
        }

    def test_get_redirects_when_logged_out(self):
        """Anonymous users should be redirected to login."""
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 302)
        self.assertIn("/login", r["Location"])

    def test_get_renders_when_logged_in(self):
        """Authenticated users should see the edit profile form."""
        self.login()
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 200)
        self.assertIn("user", r.context)
        self.assertEqual(r.context["user"].pk, self.user.pk)

    def test_post_updates_basic_fields(self):
        """POST should update first/last/username/email."""
        self.login()
        data = self.base_payload() | {"first_name": "Jon", "username": "john2", "email": "john2@ex.com"}
        r = self.client.post(self.url, data, follow=True)
        self.user.refresh_from_db()
        self.assertEqual(r.status_code, 200)
        self.assertEqual(self.user.first_name, "Jon")
        self.assertEqual(self.user.username, "john2")

    def test_post_updates_password_if_provided(self):
        """POST should change password if password field is set."""
        self.login()
        data = self.base_payload() | {"password": "NewPass123!"}
        r = self.client.post(self.url, data, follow=True)
        self.user.refresh_from_db()
        self.assertEqual(r.status_code, 200)
        self.assertTrue(self.user.check_password("NewPass123!"))

    def test_post_saves_profile_picture(self):
        """POST should save an uploaded profile picture."""
        self.login()
        img = SimpleUploadedFile("a.jpg", b"\xff\xd8\xff\xe0" + b"0" * 20, content_type="image/jpeg")
        data = self.base_payload() | {"profile_picture": img}
        r = self.client.post(self.url, data, follow=True)
        self.user.refresh_from_db()
        self.assertEqual(r.status_code, 200)
        self.assertTrue(bool(self.user.profile_picture))

    def test_post_duplicate_username_shows_error(self):
        """Duplicate username should render form with error message."""
        User = get_user_model()
        User.objects.create_user(
            username="taken",
            email="taken@example.com",
            password="Pass12345!",
        )
        self.login()
        data = self.base_payload() | {"username": "taken"}
        r = self.client.post(self.url, data)
        self.assertEqual(r.status_code, 200)
        self.assertIn("error", r.context)

    def test_post_blank_password_does_not_change_password(self):
        """Blank password should not update the stored password."""
        self.login()
        old_hash = get_user_model().objects.get(pk=self.user.pk).password
        r = self.client.post(self.url, self.base_payload() | {"password": ""})
        self.user.refresh_from_db()
        self.assertEqual(r.status_code, 302)
        self.assertEqual(self.user.password, old_hash)

    def test_post_with_picture_(self):
        """Posting a file should execute the profile_picture branch."""
        self.login()
        img = SimpleUploadedFile("a.jpg", b"\xff\xd8\xff\xe0" + b"0" * 20, content_type="image/jpeg")
        data = self.base_payload() | {"profile_picture": img}
        r = self.client.post(self.url, data)
        self.user.refresh_from_db()
        self.assertEqual(r.status_code, 302)
        self.assertTrue(bool(self.user.profile_picture))

    def test_post_duplicate_email_renders_error(self):
        """Duplicate email should execute IntegrityError branch."""
        User = get_user_model()
        User.objects.create_user(username="x", email="dup@example.com", password="Pass12345!")
        self.login()
        data = self.base_payload() | {"email": "dup@example.com"}
        r = self.client.post(self.url, data)
        self.assertEqual(r.status_code, 200)
        self.assertIn("error", r.context)

    def test_post_redirects_when_logged_out(self):
        """Anonymous POST should redirect to login."""
        r = self.client.post(self.url, self.base_payload())
        self.assertEqual(r.status_code, 302)
        self.assertIn("/login", r["Location"])
