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
from tickets.models import (
    Ticket,
    TicketParticipant,
    Department,
    UserDepartments,
)


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
        self.assertEqual(r.context["assigned_active_count"], 0)
        self.assertEqual(r.context["assigned_completed_count"], 0)
        self.assertEqual(r.context["created_total_count"], 0)
        self.assertEqual(r.context["created_closed_count"], 0)
        self.assertEqual(r.context["department_count"], 0)
        self.assertEqual(r.context["departments"], [])

    def test_views_self_sets_flag_true(self):
        """Viewing own slug sets is_own_profile True."""
        self.login()
        url = reverse("profile", kwargs={"profile_slug": self.user.profile_slug})
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.context["is_own_profile"])
        self.assertEqual(r.context["profile_user"].pk, self.user.pk)

    def _create_profile_stats_fixtures(self):
        """Create tickets and departments used by stats tests."""
        tickets_data = [
            ("Open ticket by self", Ticket.Status.OPEN, self.user),
            ("Another Open ticket", Ticket.Status.OPEN, self.user),
            ("Closed ticket by other", Ticket.Status.CLOSED, self.other),
        ]
        tickets = [
            Ticket.objects.create(title=title, status=status, created_by=creator)
            for title, status, creator in tickets_data
        ]
        Ticket.objects.create(
            title="Unrelated closed ticket",
            status=Ticket.Status.CLOSED,
            created_by=self.user,
        )
        for ticket in tickets:
            TicketParticipant.objects.create(ticket=ticket, user=self.other)
        for name in ["Support", "Billing"]:
            dept = Department.objects.create(name=name, created_by=self.user)
            UserDepartments.objects.create(user=self.other, department=dept)

    def test_profile_stats_reflect_tickets_and_departments(self):
        """Profile view exposes correct ticket and department stats."""
        self.login()
        self._create_profile_stats_fixtures()

        url = reverse("profile", kwargs={"profile_slug": self.other.profile_slug})
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)

        self.assertEqual(r.context["assigned_active_count"], 2)
        self.assertEqual(r.context["assigned_completed_count"], 1)

        self.assertEqual(r.context["created_total_count"], 1)
        self.assertEqual(r.context["created_closed_count"], 1)

        self.assertEqual(r.context["department_count"], 2)
        self.assertCountEqual(
            [department.name for department in r.context["departments"]],
            ["Support", "Billing"],
        )

    def test_profile_departments_render_as_links(self):
        """Profile departments should link to department pages."""
        self.login()
        department = Department.objects.create(name="Support", created_by=self.user)
        UserDepartments.objects.create(user=self.other, department=department)

        response = self.client.get(
            reverse("profile", kwargs={"profile_slug": self.other.profile_slug})
        )

        self.assertContains(response, reverse("department", args=[department.slug]))

    def test_unknown_slug_returns_404(self):
        """Unknown slugs should return a 404."""
        self.login()
        url = reverse("profile", kwargs={"profile_slug": "no-such-user"})
        r = self.client.get(url)
        self.assertEqual(r.status_code, 404)
