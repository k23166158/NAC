from django.test import TestCase, Client
from django.urls import reverse


class UnauthenticatedHomeViewTests(TestCase):
    """Tests for the UnauthenticatedHomeView."""

    def setUp(self):
        """Set up test client."""
        self.client = Client()
        self.url = reverse("unauthenticated_home")

    def test_unauthenticated_home_view_returns_200(self):
        """Unauthenticated home view should return 200 status."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_unauthenticated_home_view_renders_correct_template(self):
        """Unauthenticated home view should render unauthenticated_home template."""
        response = self.client.get(self.url)
        self.assertTemplateUsed(response, "unauthenticated_home.html")

    def test_unauthenticated_home_view_uses_base_template(self):
        """Unauthenticated home view should extend base template."""
        response = self.client.get(self.url)
        self.assertTemplateUsed(response, "base.html")

    def test_unauthenticated_home_view_get_method(self):
        """GET method should be allowed for unauthenticated home view."""
        response = self.client.get(self.url)
        self.assertNotEqual(response.status_code, 405)

    def test_unauthenticated_home_view_context_empty(self):
        """Unauthenticated home view should render with empty context."""
        response = self.client.get(self.url)
        self.assertIsNotNone(response.context)

    def test_unauthenticated_home_view_content_type(self):
        """Response should have correct content type."""
        response = self.client.get(self.url)
        self.assertEqual(response["Content-Type"], "text/html; charset=utf-8")

    def test_unauthenticated_home_view_post_not_allowed(self):
        """POST method should not be allowed for unauthenticated home view."""
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, 405)

    def test_unauthenticated_home_view_put_not_allowed(self):
        """PUT method should not be allowed for unauthenticated home view."""
        response = self.client.put(self.url)
        self.assertEqual(response.status_code, 405)

    def test_unauthenticated_home_view_delete_not_allowed(self):
        """DELETE method should not be allowed for unauthenticated home view."""
        response = self.client.delete(self.url)
        self.assertEqual(response.status_code, 405)
