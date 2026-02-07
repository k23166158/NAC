from datetime import timedelta

from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from django.contrib.auth import get_user_model

from tickets.models import Ticket, TicketMessage  # adjust import if needed
from tickets.models.ticket_participant import TicketParticipant  # adjust import if needed

User = get_user_model()

class HomeViewTests(TestCase):
    """Tests for the Home view."""

    def setUp(self):
        """Set up test users and client."""
        self.client = Client()
        self.url = reverse("home")
        mapping = [
            ("user", "homeuser", "Home", "User", False),
            ("staff1", "staff1", "Staff", "One", True),
            ("staff2", "staff2", "Staff", "Two", True),
        ]
        for attr, username, fname, lname, is_staff in mapping:
            u = User.objects.create_user(username=username, password="password123",
                                         email=f"{username}@example.com",
                                         first_name=fname, last_name=lname, is_staff=is_staff)
            setattr(self, attr, u)

    # ------------------------
    # Basic access
    # ------------------------

    def test_home_view_anonymous(self):
        """Anonymous users should see landing page."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "unauthenticated_home.html")

    def test_home_view_authenticated_student(self):
        """Student should see home page."""
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "home_view.html")

    def test_home_view_authenticated_staff(self):
        """Staff should see home page."""
        self.client.force_login(self.staff1)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "home_view.html")

    # ------------------------
    # Student visibility
    # ------------------------

    def test_student_only_sees_own_tickets(self):
        """Non-staff only sees tickets they created."""
        other = User.objects.create_user(
            username="otheruser",
            password="password123",
            email="other@example.com",
            first_name="Other",
            last_name="User",
            is_staff=False,
        )

        my_ticket = Ticket.objects.create(title="Mine", created_by=self.user, status=Ticket.Status.OPEN)
        other_ticket = Ticket.objects.create(title="Not mine", created_by=other, status=Ticket.Status.OPEN)

        self.client.force_login(self.user)
        response = self.client.get(self.url)

        active_ids = list(response.context["active_tickets"].values_list("id", flat=True))
        self.assertIn(my_ticket.id, active_ids)
        self.assertNotIn(other_ticket.id, active_ids)

    # ------------------------
    # Staff visibility rules
    # ------------------------

    def test_staff_does_not_see_all_tickets_by_default(self):
        """
        Staff should NOT automatically see everyone's tickets
        unless participant or has messaged (or created).
        """
        t = Ticket.objects.create(title="Student ticket", created_by=self.user, status=Ticket.Status.OPEN)

        self.client.force_login(self.staff1)
        response = self.client.get(self.url)

        active_ids = list(response.context["active_tickets"].values_list("id", flat=True))
        self.assertNotIn(t.id, active_ids)

    def test_staff_sees_ticket_if_they_sent_a_message_on_it(self):
        """If staff sent a message in the ticket, it should appear for them."""
        t = Ticket.objects.create(title="Needs staff reply", created_by=self.user, status=Ticket.Status.OPEN)

        # staff message links staff to ticket (via ticketmessage__sender=user)
        TicketMessage.objects.create(ticket=t, sender=self.staff1, body="Staff reply")

        self.client.force_login(self.staff1)
        response = self.client.get(self.url)

        active_ids = list(response.context["active_tickets"].values_list("id", flat=True))
        self.assertIn(t.id, active_ids)

    def test_staff_sees_ticket_if_forwarded_as_participant(self):
        """If staff is a TicketParticipant, they should see it."""
        t = Ticket.objects.create(title="Forwarded ticket", created_by=self.user, status=Ticket.Status.OPEN)

        TicketParticipant.objects.create(ticket=t, user=self.staff2)

        self.client.force_login(self.staff2)
        response = self.client.get(self.url)

        active_ids = list(response.context["active_tickets"].values_list("id", flat=True))
        self.assertIn(t.id, active_ids)

    def test_forwarded_staff_does_not_make_other_staff_see_it(self):
        """Forwarding to staff2 should not automatically expose to staff1."""
        t = Ticket.objects.create(title="Forwarded ticket", created_by=self.user, status=Ticket.Status.OPEN)
        TicketParticipant.objects.create(ticket=t, user=self.staff2)

        self.client.force_login(self.staff1)
        response = self.client.get(self.url)

        active_ids = list(response.context["active_tickets"].values_list("id", flat=True))
        self.assertNotIn(t.id, active_ids)

    # ------------------------
    # Ticket status routing
    # ------------------------

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

    # ------------------------
    # Overdue logic
    # ------------------------

    def test_overdue_requires_last_message_older_than_7_days_and_from_non_staff(self):
        """
        Overdue = ticket is OPEN/PENDING AND last_message_at < cutoff AND last sender is not staff.
        """
        t = Ticket.objects.create(title="Should be overdue", created_by=self.user, status=Ticket.Status.OPEN)

        msg = TicketMessage.objects.create(ticket=t, sender=self.user, body="User asked something")
        old_time = timezone.now() - timedelta(days=8)
        TicketMessage.objects.filter(pk=msg.pk).update(created_at=old_time, edited_at=old_time)

        self.client.force_login(self.user)
        response = self.client.get(self.url)

        overdue_ids = list(response.context["overdue_tickets"].values_list("id", flat=True))
        active_ids = list(response.context["active_tickets"].values_list("id", flat=True))

        self.assertIn(t.id, overdue_ids)
        self.assertNotIn(t.id, active_ids)

    def test_not_overdue_if_last_message_is_from_staff_even_if_old(self):
        """If the last message is from staff, it should NOT be overdue."""
        t = Ticket.objects.create(title="Not overdue due to staff last", created_by=self.user, status=Ticket.Status.OPEN)

        m1 = TicketMessage.objects.create(ticket=t, sender=self.user, body="User ping")
        old_m1 = timezone.now() - timedelta(days=10)
        TicketMessage.objects.filter(pk=m1.pk).update(created_at=old_m1, edited_at=old_m1)

        m2 = TicketMessage.objects.create(ticket=t, sender=self.staff1, body="Staff replied")
        old_m2 = timezone.now() - timedelta(days=8)
        TicketMessage.objects.filter(pk=m2.pk).update(created_at=old_m2, edited_at=old_m2)

        self.client.force_login(self.user)
        response = self.client.get(self.url)

        overdue_ids = list(response.context["overdue_tickets"].values_list("id", flat=True))
        active_ids = list(response.context["active_tickets"].values_list("id", flat=True))

        self.assertNotIn(t.id, overdue_ids)
        self.assertIn(t.id, active_ids)

    def test_not_overdue_if_last_message_is_recent(self):
        """If the last message is within 7 days, it should be active not overdue."""
        t = Ticket.objects.create(title="Recent message", created_by=self.user, status=Ticket.Status.OPEN)
        TicketMessage.objects.create(ticket=t, sender=self.user, body="Recent ping")

        self.client.force_login(self.user)
        response = self.client.get(self.url)

        overdue_ids = list(response.context["overdue_tickets"].values_list("id", flat=True))
        active_ids = list(response.context["active_tickets"].values_list("id", flat=True))

        self.assertNotIn(t.id, overdue_ids)
        self.assertIn(t.id, active_ids)

    # ------------------------
    # Annotation checks
    # ------------------------

    def test_ticket_annotations_exist_in_queryset(self):
        """Annotated fields should exist on tickets returned to the template."""
        t = Ticket.objects.create(title="Annotated", created_by=self.user, status=Ticket.Status.OPEN)
        TicketMessage.objects.create(ticket=t, sender=self.user, body="Hello")

        self.client.force_login(self.user)
        response = self.client.get(self.url)

        ticket = response.context["active_tickets"].first()
        self.assertIsNotNone(ticket)

        self.assertTrue(hasattr(ticket, "last_message_at"))
        self.assertTrue(hasattr(ticket, "last_message_body"))
        self.assertTrue(hasattr(ticket, "last_message_sender_id"))
        self.assertTrue(hasattr(ticket, "last_sender_is_staff"))
        self.assertTrue(hasattr(ticket, "last_sender_first"))
        self.assertTrue(hasattr(ticket, "last_sender_last"))

        self.assertIsNotNone(ticket.last_message_at)
        self.assertEqual(ticket.last_message_body, "Hello")