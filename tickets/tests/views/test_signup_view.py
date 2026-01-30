import tempfile
from django.test import TestCase, Client, override_settings
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile


User = get_user_model()

TEMP_MEDIA_ROOT = tempfile.mkdtemp()


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class SignUpViewTests(TestCase):
    """Tests for SignUpView: GET/POST behaviour, rule enforcement, uploads, redirects."""

    def setUp(self):
        """Set up test client and url."""
        self.client = Client()
        self.signup_url = reverse("signup")

    def test_signup_get_renders_template(self):
        """GET /signup/ should render signup.html and provide a form."""
        response = self.client.get(self.signup_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "signup.html")
        self.assertIn("form", response.context)

    def test_signup_redirects_if_authenticated(self):
        """Authenticated users should be redirected away from signup to home."""
        user = User.objects.create_user(
            username="u1",
            password="StrongPass123!!",
            first_name="A",
            last_name="B",
            email="u1@example.com",
        )
        self.client.force_login(user)

        response = self.client.get(self.signup_url)
        self.assertRedirects(response, reverse("home"), fetch_redirect_response=False)

    def test_signup_post_valid_creates_user_enforces_flags_logs_in_and_redirects(self):
        """
        Valid POST should:
        - create the user
        - normalize email
        - enforce is_staff False, is_superuser False, is_active True
        - log the user in
        - redirect to home
        """
        response = self.client.post(self.signup_url, data={
            "username": "newuser",
            "first_name": "First",
            "last_name": "Last",
            "email": "  NewUser@Example.com ",
            "bio": "Hello",
            "password1": "StrongPass123!!",
            "password2": "StrongPass123!!",
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("home"))
        user = User.objects.get(username="newuser")
        self.assertEqual(user.email, "newuser@example.com")
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertTrue(user.is_active)
        self.assertIn("_auth_user_id", self.client.session)

    def test_signup_post_invalid_re_renders_and_creates_no_user(self):
        """Invalid POST should re-render signup.html and not create a user."""
        response = self.client.post(self.signup_url, data={
            "username": "baduser",
            "first_name": "Bad",
            "last_name": "User",
            "email": "bad@example.com",
            "password1": "StrongPass123!!",
            "password2": "DifferentPass123!!",
        })

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "signup.html")
        self.assertFalse(User.objects.filter(username="baduser").exists())

    def test_signup_accepts_profile_picture_upload(self):
        """POST with profile_picture should save the uploaded file to the user model."""
        # Tiny valid GIF bytes
        gif_bytes = (
            b"GIF89a\x01\x00\x01\x00\x80\x00\x00"
            b"\x00\x00\x00\xff\xff\xff!\xf9\x04\x01"
            b"\x00\x00\x00\x00,\x00\x00\x00\x00\x01"
            b"\x00\x01\x00\x00\x02\x02D\x01\x00;"
        )
        upload = SimpleUploadedFile("avatar.gif", gif_bytes, content_type="image/gif")

        response = self.client.post(self.signup_url, data={
            "username": "picuser",
            "first_name": "Pic",
            "last_name": "User",
            "email": "picuser@example.com",
            "bio": "",
            "password1": "StrongPass123!!",
            "password2": "StrongPass123!!",
            "profile_picture": upload,
        })

        self.assertEqual(response.status_code, 302)
        user = User.objects.get(username="picuser")
        self.assertTrue(bool(user.profile_picture))
        self.assertIn("profile_pictures/", user.profile_picture.name)
