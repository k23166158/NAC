from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model

User = get_user_model()

class HomeViewTests(TestCase):
    """Tests for the Home view."""

    def setUp(self):
        """Set up the test client and user."""
        self.client = Client()
        self.url = reverse('home')
        self.user = User.objects.create_user(username='homeuser', password='password123')

    def test_home_view_anonymous(self):
        """Anonymous users should see the landing page."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'landing.html') #

    def test_home_view_authenticated(self):
        """Authenticated users should see the home dashboard."""
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'home.html') #