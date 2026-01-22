from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model

User = get_user_model()

class AuthViewTests(TestCase):
    """Tests for authentication views."""

    def setUp(self):
        """Set up the test client and user."""
        self.client = Client()
        self.login_url = reverse('login')
        self.user = User.objects.create_user(username='authuser', password='password123')

    def test_login_view_renders_for_anonymous(self):
        """GET /login/ should render the login template."""
        response = self.client.get(self.login_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'login.html')

    def test_login_view_redirects_authenticated(self):
        """Authenticated users visiting /login/ should be redirected."""
        self.client.force_login(self.user)
        response = self.client.get(self.login_url)
        self.assertRedirects(response, reverse('home'), fetch_redirect_response=False)