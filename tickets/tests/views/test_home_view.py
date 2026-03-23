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
        active_tickets = list(res.context["active_tickets"])
        self.assertIn(t1, active_tickets)
        self.assertTrue(active_tickets[0].is_overdue)
        self.assertEqual(active_tickets[0].last_message_body, "Ping")

        TicketMessage.objects.create(ticket=t1, sender=self.s1, body="Staff reply")
        res2 = self.c.get(self.url)
        self.assertFalse(list(res2.context["active_tickets"])[0].is_overdue)

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

    def test_home_includes_integrated_search_filters(self):
        """Home should expose the integrated ticket search controls and filter state."""
        self.c.force_login(self.s1)
        response = self.c.get(self.url, {"q": "exam", "tab": "completed"})

        self.assertContains(response, "Search title, message body, creator, or email")
        self.assertContains(response, 'id="scopeSelect"')
        self.assertContains(response, "Your ticket")
        self.assertContains(response, 'id="searchCollapseToggle"')
        self.assertEqual(response.context["filters"]["q"], "exam")
        self.assertEqual(response.context["scope_options"], ["personal", "department", "assigned"])

    def test_home_filters_narrow_ticket_lists(self):
        """Home ticket lists should respect the integrated search filters."""
        dept = Department.objects.create(name="Support", created_by=self.s1)
        UserDepartments.objects.create(user=self.s1, department=dept)
        match = Ticket.objects.create(title="Exam issue", created_by=self.u, status=Ticket.Status.OPEN)
        miss = Ticket.objects.create(title="Library issue", created_by=self.u, status=Ticket.Status.OPEN)
        TicketAssigned.objects.create(ticket=match, department=dept)
        TicketAssigned.objects.create(ticket=miss, department=dept)
        TicketMessage.objects.create(ticket=match, sender=self.u, body="Exam body")
        TicketMessage.objects.create(ticket=miss, sender=self.u, body="Library body")

        self.c.force_login(self.s1)
        response = self.c.get(self.url, {"scope": "department", "q": "Exam", "status": "open"})

        self.assertIn(match, response.context["active_tickets"])
        self.assertNotIn(miss, response.context["active_tickets"])

    def test_home_ticket_row_profile_links_render(self):
        """Home ticket rows should link creator and latest sender profiles."""
        ticket = Ticket.objects.create(
            title="Linked ticket", created_by=self.u, status=Ticket.Status.OPEN
        )
        TicketMessage.objects.create(ticket=ticket, sender=self.s1, body="Latest")

        self.c.force_login(self.u)
        response = self.c.get(self.url)

        self.assertContains(response, reverse("profile", args=[self.u.profile_slug]))
        self.assertContains(response, reverse("profile", args=[self.s1.profile_slug]))

    def test_home_assigned_staff_filter_excludes_unassigned_tickets(self):
        """Assigned-staff filter should only show tickets that include that staff user."""
        dept = Department.objects.create(name="Support", created_by=self.s1)
        UserDepartments.objects.create(user=self.s1, department=dept)

        assigned_to_s1 = Ticket.objects.create(
            title="Assigned to s1", created_by=self.u, status=Ticket.Status.OPEN
        )
        not_assigned_to_s1 = Ticket.objects.create(
            title="Assigned to s2 only", created_by=self.u, status=Ticket.Status.OPEN
        )

        TicketAssigned.objects.create(ticket=assigned_to_s1, department=dept)
        TicketAssigned.objects.create(ticket=not_assigned_to_s1, department=dept)
        TicketParticipant.objects.create(ticket=assigned_to_s1, user=self.s1, removed_self=False)
        TicketParticipant.objects.create(ticket=not_assigned_to_s1, user=self.s2, removed_self=False)

        self.c.force_login(self.s1)
        response = self.c.get(
            self.url,
            {"scope": "department", "assigned_staff": str(self.s1.id)},
        )

        self.assertIn(assigned_to_s1, response.context["active_tickets"])
        self.assertNotIn(not_assigned_to_s1, response.context["active_tickets"])

    def test_home_assigned_staff_filter_invalid_value_returns_no_tickets(self):
        """Invalid assigned-staff values should not return unrelated tickets."""
        dept = Department.objects.create(name="Support", created_by=self.s1)
        UserDepartments.objects.create(user=self.s1, department=dept)
        ticket = Ticket.objects.create(title="Open ticket", created_by=self.u, status=Ticket.Status.OPEN)
        TicketAssigned.objects.create(ticket=ticket, department=dept)
        TicketParticipant.objects.create(ticket=ticket, user=self.s1, removed_self=False)

        self.c.force_login(self.s1)
        response = self.c.get(
            self.url,
            {"scope": "department", "assigned_staff": "user-x"},
        )

        self.assertNotIn(ticket, response.context["active_tickets"])

    def test_home_assigned_staff_filter_excludes_ticket_creator(self):
        """Assigned-staff filter should not treat ticket creator as assigned staff."""
        dept = Department.objects.create(name="Support", created_by=self.s1)
        UserDepartments.objects.create(user=self.s1, department=dept)

        creator = User.objects.create_user(
            username="creator",
            email="creator@example.com",
            password="p",
            is_staff=True,
        )
        creator_ticket = Ticket.objects.create(
            title="Creator ticket", created_by=creator, status=Ticket.Status.OPEN
        )
        TicketAssigned.objects.create(ticket=creator_ticket, department=dept)
        # Even if a participant row exists for creator, creator should not count as "assigned staff".
        TicketParticipant.objects.create(ticket=creator_ticket, user=creator, removed_self=False)

        self.c.force_login(self.s1)
        response = self.c.get(
            self.url,
            {"scope": "department", "assigned_staff": str(creator.id)},
        )

        self.assertNotIn(creator_ticket, response.context["active_tickets"])

    def test_home_staff_options_follow_selected_department(self):
        """Assigned-staff options should narrow to members of the selected department."""
        s3 = User.objects.create_user(
            username="s3", email="s3@e.com", password="p", is_staff=True
        )
        support = Department.objects.create(name="Support", created_by=self.s1)
        registry = Department.objects.create(name="Registry", created_by=self.s1)
        UserDepartments.objects.create(user=self.s1, department=support)
        UserDepartments.objects.create(user=s3, department=support)
        UserDepartments.objects.create(user=self.s2, department=registry)
        ticket = Ticket.objects.create(title="Scoped", created_by=self.u, status=Ticket.Status.OPEN)
        TicketAssigned.objects.create(ticket=ticket, department=support)
        TicketParticipant.objects.create(ticket=ticket, user=self.s1)
        TicketParticipant.objects.create(ticket=ticket, user=s3)
        TicketParticipant.objects.create(ticket=ticket, user=self.s2)

        self.c.force_login(self.s1)
        response = self.c.get(self.url, {"scope": "department", "department": str(support.id)})

        self.assertNotIn(self.s1, list(response.context["staff_users"]))
        self.assertIn(s3, list(response.context["staff_users"]))
        self.assertNotIn(self.s2, list(response.context["staff_users"]))

    def test_home_department_options_follow_selected_staff(self):
        """Department options should narrow to departments for the selected staff user."""
        support = Department.objects.create(name="Support", created_by=self.s1)
        registry = Department.objects.create(name="Registry", created_by=self.s1)
        UserDepartments.objects.create(user=self.s1, department=support)
        UserDepartments.objects.create(user=self.s2, department=registry)
        ticket = Ticket.objects.create(title="Scoped", created_by=self.u, status=Ticket.Status.OPEN)
        TicketAssigned.objects.create(ticket=ticket, department=support)
        TicketAssigned.objects.create(ticket=ticket, department=registry)
        TicketParticipant.objects.create(ticket=ticket, user=self.s1)
        TicketParticipant.objects.create(ticket=ticket, user=self.s2)

        self.c.force_login(self.s1)
        response = self.c.get(self.url, {"scope": "department", "assigned_staff": str(self.s1.id)})

        self.assertIn(support, list(response.context["departments"]))
        self.assertNotIn(registry, list(response.context["departments"]))

    def test_home_preserves_display_count_for_dependent_refresh(self):
        """Dependent filter refreshes should keep the visible-count label until apply."""
        support = Department.objects.create(name="Support", created_by=self.s1)
        registry = Department.objects.create(name="Registry", created_by=self.s1)
        UserDepartments.objects.create(user=self.s1, department=support)
        UserDepartments.objects.create(user=self.s1, department=registry)
        match = Ticket.objects.create(title="Support only", created_by=self.u, status=Ticket.Status.OPEN)
        miss = Ticket.objects.create(title="Registry only", created_by=self.u, status=Ticket.Status.OPEN)
        TicketAssigned.objects.create(ticket=match, department=support)
        TicketAssigned.objects.create(ticket=miss, department=registry)

        self.c.force_login(self.s1)
        response = self.c.get(
            self.url,
            {
                "scope": "department",
                "department": str(support.id),
                "auto_refresh": "dependent",
                "display_count": "2",
            },
        )

        self.assertEqual(response.context["visible_ticket_count"], 1)
        self.assertEqual(response.context["display_visible_ticket_count"], 2)

    def _staff_dependent_refresh_response(self):
        """Return a dependent-refresh response with an assigned-staff filter."""
        support = Department.objects.create(name="Support", created_by=self.s1)
        UserDepartments.objects.create(user=self.s1, department=support)
        match = Ticket.objects.create(title="Assigned to s1", created_by=self.u, status=Ticket.Status.OPEN)
        miss = Ticket.objects.create(title="Assigned to s2", created_by=self.u, status=Ticket.Status.OPEN)
        TicketAssigned.objects.create(ticket=match, department=support)
        TicketAssigned.objects.create(ticket=miss, department=support)
        TicketParticipant.objects.create(ticket=match, user=self.s1, removed_self=False)
        TicketParticipant.objects.create(ticket=miss, user=self.s2, removed_self=False)
        self.c.force_login(self.s1)
        return self.c.get(
            self.url,
            {
                "scope": "department",
                "assigned_staff": str(self.s1.id),
                "auto_refresh": "dependent",
                "display_count": "2",
                "applied_q": "",
                "applied_status": "",
                "applied_department": "",
                "applied_assigned_staff": "",
                "applied_created_from": "",
                "applied_created_to": "",
            },
        )

    def test_home_preserves_display_count_for_staff_dependent_refresh(self):
        """Assigned-staff dependent refresh should keep the visible-count label until apply."""
        response = self._staff_dependent_refresh_response()
        self.assertEqual(response.context["filters"]["assigned_staff"], str(self.s1.id))
        self.assertEqual(response.context["applied_filters"]["assigned_staff"], "")
        self.assertEqual(response.context["visible_ticket_count"], 2)
        self.assertEqual(response.context["display_visible_ticket_count"], 2)

    def _dependent_refresh_request(self, department_id):
        """Return a dependent-refresh home response for the selected department."""
        return self.c.get(
            self.url,
            {
                "scope": "department",
                "department": str(department_id),
                "auto_refresh": "dependent",
                "display_count": "2",
                "applied_q": "",
                "applied_status": "",
                "applied_department": "",
                "applied_assigned_staff": "",
                "applied_created_from": "",
                "applied_created_to": "",
            },
        )

    def test_home_preserves_ticket_lists_for_dependent_refresh(self):
        """Dependent refreshes should not change active/completed lists until apply."""
        support = Department.objects.create(name="Support", created_by=self.s1)
        registry = Department.objects.create(name="Registry", created_by=self.s1)
        UserDepartments.objects.create(user=self.s1, department=support)
        UserDepartments.objects.create(user=self.s1, department=registry)
        support_ticket = Ticket.objects.create(title="Support", created_by=self.u, status=Ticket.Status.OPEN)
        registry_ticket = Ticket.objects.create(title="Registry", created_by=self.u, status=Ticket.Status.OPEN)
        TicketAssigned.objects.create(ticket=support_ticket, department=support)
        TicketAssigned.objects.create(ticket=registry_ticket, department=registry)

        self.c.force_login(self.s1)
        response = self._dependent_refresh_request(support.id)

        self.assertEqual(response.context["filters"]["department"], str(support.id))
        self.assertEqual(response.context["applied_filters"]["department"], "")
        self.assertIn(support_ticket, response.context["active_tickets"])
        self.assertIn(registry_ticket, response.context["active_tickets"])

    def test_removed_user_does_not_see_ticket_in_any_scope(self):
        """Once removed (by self or others), a user should not see the ticket in any scope."""
        dept = Department.objects.create(name="D", created_by=self.s1)
        UserDepartments.objects.create(user=self.s1, department=dept)
        t = Ticket.objects.create(
            title="Scoped ticket", created_by=self.s1, status=Ticket.Status.OPEN
        )
        TicketAssigned.objects.create(ticket=t, department=dept)
        TicketParticipant.objects.create(ticket=t, user=self.s1)

        TicketParticipant.objects.filter(ticket=t, user=self.s1).update(removed_self=True)

        self.c.force_login(self.s1)

        # Personal scope
        res_personal = self.c.get(self.url, {"scope": "personal"})
        self.assertNotIn(t, res_personal.context["active_tickets"])

        # Department scope
        res_dept = self.c.get(self.url, {"scope": "department"})
        self.assertNotIn(t, res_dept.context["active_tickets"])

        # Assigned scope
        res_assigned = self.c.get(self.url, {"scope": "assigned"})
        self.assertNotIn(t, res_assigned.context["active_tickets"])
