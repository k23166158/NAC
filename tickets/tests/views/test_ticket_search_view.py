from django.test import TestCase
from django.urls import reverse


class TicketSearchRouteTests(TestCase):
    """Tests for the legacy ticket-search route."""

    def setUp(self):
        """Store the legacy ticket-search URL."""
        self.url = reverse("ticket_search")

    def test_ticket_search_redirects_to_home(self):
        """The legacy ticket-search route should redirect to home."""
        response = self.client.get(self.url)

        self.assertRedirects(response, reverse("home"))

    def test_ticket_search_redirect_preserves_querystring(self):
        """The legacy route should preserve search parameters during redirect."""
        response = self.client.get(self.url, {"scope": "department", "q": "laptop"})

        self.assertRedirects(response, f'{reverse("home")}?scope=department&q=laptop')
