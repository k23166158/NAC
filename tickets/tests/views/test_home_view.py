from datetime import timedelta

from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from django.contrib.auth import get_user_model

from tickets.models import Ticket, TicketMessage  # adjust import path if needed

User = get_user_model()


class HomeViewTests(TestCase):
    """Tests for the Home view."""

    def setUp(self):
        """Set up the test client and user."""
        self.client = Client()
        self.url = reverse("home")

        self.user = User.objects.create_user(
            username="homeuser",
            password="password123",
            email="homeuser@example.com",
            first_name="Home",
            last_name="User",
        )

        # staff user used to simulate staff replies
        self.staff = User.objects.create_user(
            username="staffuser",
            password="password123",
            email="staff@example.com",
            first_name="Staff",
            last_name="User",
            is_staff=True,
        )

    def test_home_view_anonymous(self):
        """Anonymous users should see the landing page."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "landing.html")

    def test_home_view_authenticated(self):
        """Authenticated users should see the home dashboard."""
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "home.html")

    def test_home_view_only_shows_current_users_tickets(self):
        """Tickets should be filtered to created_by=request.user."""
        other = User.objects.create_user(
            username="otheruser",
            password="password123",
            email="other@example.com",
            first_name="Other",
            last_name="User",
        )

        my_ticket = Ticket.objects.create(title="Mine", created_by=self.user, status=Ticket.Status.OPEN)
        other_ticket = Ticket.objects.create(title="Not mine", created_by=other, status=Ticket.Status.OPEN)

        self.client.force_login(self.user)
        response = self.client.get(self.url)

        active_ids = list(response.context["active_tickets"].values_list("id", flat=True))
        self.assertIn(my_ticket.id, active_ids)
        self.assertNotIn(other_ticket.id, active_ids)

    def test_completed_tickets_go_to_completed(self):
        """Closed tickets appear under completed_tickets."""
        closed = Ticket.objects.create(title="Closed ticket", created_by=self.user, status=Ticket.Status.CLOSED)
        open_t = Ticket.objects.create(title="Open ticket", created_by=self.user, status=Ticket.Status.OPEN)

        self.client.force_login(self.user)
        response = self.client.get(self.url)

        completed_ids = list(response.context["completed_tickets"].values_list("id", flat=True))
        active_ids = list(response.context["active_tickets"].values_list("id", flat=True))

        self.assertIn(closed.id, completed_ids)
        self.assertNotIn(closed.id, active_ids)
        self.assertIn(open_t.id, active_ids)

    def test_overdue_requires_last_message_older_than_7_days_and_from_non_staff(self):
        """
        Overdue = ticket is OPEN/PENDING AND last_message_at < cutoff AND last sender is not staff.
        """
        t = Ticket.objects.create(title="Should be overdue", created_by=self.user, status=Ticket.Status.OPEN)

        # Create a message from the (non-staff) user, then manually set timestamp to old
        msg = TicketMessage.objects.create(ticket=t, sender=self.user, body="User asked something")
        TicketMessage.objects.filter(pk=msg.pk).update(timestamp=timezone.now() - timedelta(days=8))

        self.client.force_login(self.user)
        response = self.client.get(self.url)

        overdue_ids = list(response.context["overdue_tickets"].values_list("id", flat=True))
        active_ids = list(response.context["active_tickets"].values_list("id", flat=True))

        self.assertIn(t.id, overdue_ids)
        self.assertNotIn(t.id, active_ids)

    def test_not_overdue_if_last_message_is_from_staff_even_if_old(self):
        """If the last message is from staff, it should NOT be overdue."""
        t = Ticket.objects.create(title="Not overdue due to staff last", created_by=self.user, status=Ticket.Status.OPEN)

        # Old user message
        m1 = TicketMessage.objects.create(ticket=t, sender=self.user, body="User ping")
        TicketMessage.objects.filter(pk=m1.pk).update(timestamp=timezone.now() - timedelta(days=10))

        # Staff reply is the latest (make it old too, but it's the latest and from staff)
        m2 = TicketMessage.objects.create(ticket=t, sender=self.staff, body="Staff replied")
        TicketMessage.objects.filter(pk=m2.pk).update(timestamp=timezone.now() - timedelta(days=8))

        self.client.force_login(self.user)
        response = self.client.get(self.url)

        overdue_ids = list(response.context["overdue_tickets"].values_list("id", flat=True))
        active_ids = list(response.context["active_tickets"].values_list("id", flat=True))

        self.assertNotIn(t.id, overdue_ids)
        self.assertIn(t.id, active_ids)

    def test_not_overdue_if_last_message_is_recent(self):
        """If the last message is within 7 days, it should be active not overdue."""
        t = Ticket.objects.create(title="Recent message", created_by=self.user, status=Ticket.Status.OPEN)
        TicketMessage.objects.create(ticket=t, sender=self.user, body="Recent ping")  # timestamp defaults to now

        self.client.force_login(self.user)
        response = self.client.get(self.url)

        overdue_ids = list(response.context["overdue_tickets"].values_list("id", flat=True))
        active_ids = list(response.context["active_tickets"].values_list("id", flat=True))

        self.assertNotIn(t.id, overdue_ids)
        self.assertIn(t.id, active_ids)

    def test_ticket_annotations_exist_in_queryset(self):
        """Annotated fields should exist on tickets returned to the template."""
        t = Ticket.objects.create(title="Annotated", created_by=self.user, status=Ticket.Status.OPEN)
        TicketMessage.objects.create(ticket=t, sender=self.user, body="Hello")

        self.client.force_login(self.user)
        response = self.client.get(self.url)

        ticket = response.context["active_tickets"].first()
        self.assertIsNotNone(ticket)

        # These come from annotate(...)
        self.assertTrue(hasattr(ticket, "last_message_at"))
        self.assertTrue(hasattr(ticket, "last_message_body"))
        self.assertTrue(hasattr(ticket, "last_message_sender_id"))
        self.assertTrue(hasattr(ticket, "last_sender_is_staff"))
        self.assertTrue(hasattr(ticket, "last_sender_first"))
        self.assertTrue(hasattr(ticket, "last_sender_last"))

        self.assertIsNotNone(ticket.last_message_at)
        self.assertEqual(ticket.last_message_body, "Hello")