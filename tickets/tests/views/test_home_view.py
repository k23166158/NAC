from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from tickets.models import (
    Department,
    Ticket,
    TicketAssigned,
    TicketMessage,
    TicketParticipant,
    UserDepartments,
)
from tickets.views import HomeView


User = get_user_model()


class HomeViewTests(TestCase):
    """Tests for the Home view."""

    def setUp(self):
        """Setup basic users and client."""
        self.c = Client()
        self.url = reverse("home")
        self.u = User.objects.create_user(username="u", email="u@e.com", password="p")
        self.s1 = User.objects.create_user(
            username="s1", email="s1@e.com", password="p", is_staff=True
        )
        self.s2 = User.objects.create_user(
            username="s2", email="s2@e.com", password="p", is_staff=True
        )

    def test_home_routing_and_context(self):
        """Test unauthenticated, authenticated student/staff, and plus button presence."""
        self.assertEqual(self.c.get(self.url).status_code, 200)
        self.c.force_login(self.u)
        res = self.c.get(self.url)
        self.assertTemplateUsed(res, "home_view.html")
        self.assertContains(res, 'class="tab-plus"')
        self.assertContains(res, reverse("ticket_create"))
        self.c.force_login(self.s1)
        self.assertEqual(self.c.get(self.url).status_code, 200)

    def test_home_ticket_visibility(self):
        """Test ticket scoping (personal/dept/assigned) and active/closed statuses."""
        t1 = Ticket.objects.create(title="My Open", created_by=self.u, status=Ticket.Status.OPEN)
        t2 = Ticket.objects.create(title="Other Open", created_by=self.s1, status=Ticket.Status.OPEN)
        t3 = Ticket.objects.create(title="Closed", created_by=self.u, status=Ticket.Status.CLOSED)
        TicketParticipant.objects.create(ticket=t2, user=self.s2)
        dept = Department.objects.create(name="D", created_by=self.s1)
        UserDepartments.objects.create(user=self.s1, department=dept)
        TicketAssigned.objects.create(ticket=t2, department=dept)
        self.c.force_login(self.u)
        res_u = self.c.get(self.url, {"scope": "department"})
        self.assertIn(t1, res_u.context["active_tickets"])
        self.assertIn(t3, res_u.context["completed_tickets"])
        self.assertNotIn(t2, res_u.context["active_tickets"])
        self.c.force_login(self.s2)
        self.assertIn(t2, self.c.get(self.url, {"scope": "assigned"}).context["active_tickets"])
        self.assertNotIn(t2, self.c.get(self.url, {"scope": "personal"}).context["active_tickets"])
        self.c.force_login(self.s1)
        self.assertIn(t2, self.c.get(self.url, {"scope": "department"}).context["active_tickets"])

    def test_home_overdue_and_annotations(self):
        """Test overdue logic criteria and message attribute annotations."""
        t1 = Ticket.objects.create(title="T", created_by=self.u, status=Ticket.Status.OPEN)
        m = TicketMessage.objects.create(ticket=t1, sender=self.u, body="Ping")
        old = timezone.now() - timedelta(days=8)
        TicketMessage.objects.filter(pk=m.pk).update(created_at=old, edited_at=old)

        self.c.force_login(self.u)
        res = self.c.get(self.url)
        self.assertIn(t1, res.context["overdue_tickets"])
        self.assertEqual(res.context["overdue_tickets"][0].last_message_body, "Ping")

        TicketMessage.objects.create(ticket=t1, sender=self.s1, body="Staff reply")
        res2 = self.c.get(self.url)
        self.assertNotIn(t1, res2.context["overdue_tickets"])

    def test_home_internal_helpers(self):
        """Direct coverage for internal view methods to hit implicit branches."""
        view = HomeView()
        self.assertIsNone(view.base_tickets(self.u, scope="invalid"))
        qs, scope = view.handle_scope(self.s1, "invalid")
        self.assertEqual(scope, "personal")

        t = Ticket.objects.create(title="T", created_by=self.u)
        TicketMessage.objects.create(ticket=t, sender=self.s1, body="M")
        annotated = view._annotate_last_message(Ticket.objects.filter(id=t.id), self.u)
        self.assertEqual(annotated.first().last_message_body, "M")

        unread = view._annotate_unread_count(annotated, self.u)
        self.assertEqual(unread.first().unread_count, 1)

    def test_removed_user_does_not_see_ticket_in_any_scope(self):
        """Once removed (by self or others), a user should not see the ticket in any scope."""
        dept = Department.objects.create(name="D", created_by=self.s1)
        UserDepartments.objects.create(user=self.s1, department=dept)
        t = Ticket.objects.create(title="Scoped ticket", created_by=self.s1, status=Ticket.Status.OPEN)
        TicketAssigned.objects.create(ticket=t, department=dept)
        TicketParticipant.objects.create(ticket=t, user=self.s1)
        TicketParticipant.objects.filter(ticket=t, user=self.s1).update(removed_self=True)

        self.c.force_login(self.s1)
        res_personal = self.c.get(self.url, {"scope": "personal"})
        self.assertNotIn(t, res_personal.context["active_tickets"])

        # Department scope
        res_dept = self.c.get(self.url, {"scope": "department"})
        self.assertNotIn(t, res_dept.context["active_tickets"])

        # Assigned scope
        res_assigned = self.c.get(self.url, {"scope": "assigned"})
        self.assertNotIn(t, res_assigned.context["active_tickets"])