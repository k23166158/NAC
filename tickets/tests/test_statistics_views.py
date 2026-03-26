from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from tickets.models import Ticket, TicketMessage

User = get_user_model()


class AdminStatisticsViewTest(TestCase):
    """Tests for the AdminStatisticsView."""

    def setUp(self):
        """Set up users for testing."""
        self.staff_user = User.objects.create_user(
            username="staff", password="pwd", email="staff@test.com", is_staff=True
        )
        self.super_user = User.objects.create_superuser(
            username="admin", password="pwd", email="admin@test.com"
        )
        self.normal_user = User.objects.create_user(
            username="normal", password="pwd", email="normal@test.com"
        )
        self.url = reverse("admin_statistics")

    def test_access_denied_for_normal_user(self):
        """Ensure normal users cannot access admin stats."""
        self.client.login(username="normal", password="pwd")
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 403)

    def test_access_granted_for_staff(self):
        """Ensure staff users can access admin stats."""
        self.client.login(username="staff", password="pwd")
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "admin_statistics.html")

    def test_access_granted_for_superuser(self):
        """Ensure superusers can access admin stats."""
        self.client.login(username="admin", password="pwd")
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_ticket_statistics_calculation(self):
        """Test if ticket statistics are correctly calculated."""
        Ticket.objects.create(
            title="T1", created_by=self.normal_user, status=Ticket.Status.OPEN
        )
        Ticket.objects.create(
            title="T3", created_by=self.normal_user, status=Ticket.Status.CLOSED
        )

        self.client.login(username="staff", password="pwd")
        response = self.client.get(self.url)
        stats = response.context["ticket_stats"]

        self.assertEqual(stats["total"], Ticket.objects.count())
        self.assertEqual(stats["open"], Ticket.objects.filter(status=Ticket.Status.OPEN).count())
        self.assertEqual(stats["closed"], Ticket.objects.filter(status=Ticket.Status.CLOSED).count())

    def test_user_statistics_calculation(self):
        """Test if user statistics are correctly calculated."""
        t1 = Ticket.objects.create(title="T1", created_by=self.normal_user)
        t2 = Ticket.objects.create(title="T2", created_by=self.normal_user)
        TicketMessage.objects.create(ticket=t1, sender=self.staff_user, body="H")

        self.client.login(username="staff", password="pwd")
        response = self.client.get(self.url)
        user_stats = response.context["user_stats"]

        creators = user_stats["top_creators"]
        responders = user_stats["top_responders"]

        # Ensure our normal user is in creators and logic doesn't crash
        self.assertTrue(len(creators) > 0)
        self.assertTrue(len(responders) > 0)
        
        normal_stats = next(c for c in creators if c["username"] == "normal")
        self.assertEqual(normal_stats["ticket_count"], 2)
        self.assertEqual(normal_stats["profile_slug"], self.normal_user.profile_slug)

        staff_stats = next(r for r in responders if r["username"] == "staff")
        self.assertEqual(staff_stats["msgs"], 1)
        self.assertEqual(staff_stats["profile_slug"], self.staff_user.profile_slug)
        self.assertContains(response, reverse("profile", args=[self.normal_user.profile_slug]))
        self.assertContains(response, reverse("profile", args=[self.staff_user.profile_slug]))
