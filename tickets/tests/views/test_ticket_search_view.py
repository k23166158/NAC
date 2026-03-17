from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from tickets.models import Department, Ticket, TicketAssigned, TicketMessage, TicketParticipant, UserDepartments
from tickets.models.ticket_department import TicketDepartment


User = get_user_model()


class TicketSearchViewTests(TestCase):
    """Tests for the dedicated ticket search/filter page."""

    def setUp(self):
        """Create users, departments, and tickets for search scenarios."""
        self._create_users()
        self._create_departments()
        self._create_tickets()
        self.url = reverse("ticket_search")

    def _create_users(self):
        """Create users used by ticket search tests."""
        self.student = self._make_user("student", "Stu", "Dent")
        self.staff = self._make_user("staff1", "Casey", "Staff", is_staff=True)
        self.other_staff = self._make_user("staff2", "Robin", "Helper", is_staff=True)
        self.creator = self._make_user("creator", "Taylor", "Creator")

    def _make_user(self, username, first_name, last_name, **extra):
        """Create a user with stable defaults."""
        return User.objects.create_user(
            username=username,
            email=f"{username}@example.com",
            password="pwd",
            first_name=first_name,
            last_name=last_name,
            **extra,
        )

    def _create_departments(self):
        """Create departments and memberships."""
        self.support = Department.objects.create(name="Support", created_by=self.staff)
        self.registry = Department.objects.create(name="Registry", created_by=self.other_staff)
        UserDepartments.objects.create(user=self.staff, department=self.support)
        UserDepartments.objects.create(user=self.other_staff, department=self.registry)

    def _create_tickets(self):
        """Create baseline ticket fixtures for search tests."""
        self.personal_ticket = self._build_personal_ticket()
        self.department_ticket = self._build_department_ticket()
        self.assigned_ticket = self._build_assigned_ticket()
        self.foreign_ticket = self._build_foreign_ticket()

    def _build_personal_ticket(self):
        """Create a student-owned visible ticket."""
        return self._make_ticket(
            title="Laptop issue",
            creator=self.student,
            status=Ticket.Status.OPEN,
            body="My screen is flickering badly.",
        )

    def _build_department_ticket(self):
        """Create a department-scoped ticket."""
        return self._make_ticket(
            title="Exam timetable clash",
            creator=self.creator,
            status=Ticket.Status.PENDING,
            body="There is a timetable clash in my exams.",
            department=self.support,
        )

    def _build_assigned_ticket(self):
        """Create a directly assigned ticket."""
        return self._make_ticket(
            title="Library card request",
            creator=self.creator,
            status=Ticket.Status.CLOSED,
            body="Please help replace my library card.",
            participant=self.staff,
        )

    def _build_foreign_ticket(self):
        """Create a ticket outside the staff member's visible department scope."""
        return self._make_ticket(
            title="Registry-only request",
            creator=self.creator,
            status=Ticket.Status.OPEN,
            body="Only registry should see this.",
            department=self.registry,
            participant=self.other_staff,
        )

    def _make_ticket(self, *, title, creator, status, body, department=None, participant=None):
        """Create a ticket with supporting message and optional relations."""
        ticket = Ticket.objects.create(title=title, created_by=creator, status=status)
        TicketMessage.objects.create(ticket=ticket, sender=creator, body=body)
        if department:
            TicketAssigned.objects.create(ticket=ticket, department=department)
        if participant:
            TicketParticipant.objects.create(ticket=ticket, user=participant)
        return ticket

    def test_login_required(self):
        """Anonymous users should be redirected to login."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login/", response.url)

    def test_student_scope_is_forced_to_personal(self):
        """Non-staff users should only see personal-scope tickets."""
        self.client.force_login(self.student)
        response = self.client.get(self.url, {"scope": "department"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["filters"]["scope"], "personal")
        self.assertIn(self.personal_ticket, response.context["tickets"])
        self.assertNotIn(self.department_ticket, response.context["tickets"])

    def test_staff_can_search_title_body_and_creator_fields(self):
        """Search should match title, message body, and creator fields."""
        self.client.force_login(self.staff)

        response = self.client.get(self.url, {"scope": "department", "q": "timetable"})
        self.assertIn(self.department_ticket, response.context["tickets"])

        response = self.client.get(self.url, {"scope": "department", "q": "clash in my exams"})
        self.assertIn(self.department_ticket, response.context["tickets"])

        response = self.client.get(self.url, {"scope": "department", "q": "Taylor"})
        self.assertIn(self.department_ticket, response.context["tickets"])

    def test_filters_apply_status_department_and_assigned_staff(self):
        """Status, department, and assigned staff filters should narrow the queryset."""
        TicketParticipant.objects.create(ticket=self.department_ticket, user=self.staff)
        self.client.force_login(self.staff)

        response = self.client.get(
            self.url,
            {
                "scope": "department",
                "status": Ticket.Status.PENDING,
                "department": str(self.support.id),
                "assigned_staff": str(self.staff.id),
            },
        )

        self.assertEqual(list(response.context["tickets"]), [self.department_ticket])

    def test_created_date_filters_bound_results(self):
        """Created-from and created-to should filter using ticket creation date."""
        old_time = timezone.now() - timedelta(days=10)
        Ticket.objects.filter(pk=self.department_ticket.pk).update(created_at=old_time)
        today = timezone.now().date().isoformat()
        cutoff = (timezone.now() - timedelta(days=5)).date().isoformat()
        self.client.force_login(self.staff)

        response = self.client.get(self.url, {"scope": "department", "created_from": today})
        self.assertNotIn(self.department_ticket, response.context["tickets"])

        response = self.client.get(self.url, {"scope": "department", "created_to": cutoff})
        self.assertIn(self.department_ticket, response.context["tickets"])

    def test_pagination_persists_filter_querystring(self):
        """Pagination links should preserve active filters."""
        for index in range(12):
            self._make_ticket(
                title=f"Support request {index}",
                creator=self.creator,
                status=Ticket.Status.OPEN,
                body="Search pagination",
                department=self.support,
            )

        self.client.force_login(self.staff)
        response = self.client.get(self.url, {"scope": "department", "q": "Support", "page": 2})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["page_obj"].number, 2)
        self.assertEqual(response.context["pagination_query"], "&scope=department&q=Support")

    def test_empty_state_and_filter_options(self):
        """The page should render empty-state text and option datasets when no results match."""
        TicketParticipant.objects.create(ticket=self.department_ticket, user=self.staff)
        self.client.force_login(self.staff)
        response = self.client.get(self.url, {"scope": "department", "q": "does-not-exist"})

        self.assertContains(response, "No tickets match these filters.")
        departments = list(response.context["departments"])
        staff_users = list(response.context["staff_users"])
        self.assertIn(self.support, departments)
        self.assertIn(self.staff, staff_users)

    def test_staff_options_follow_selected_department(self):
        """Assigned-staff options should narrow to selected department members."""
        TicketParticipant.objects.create(ticket=self.department_ticket, user=self.staff)
        TicketParticipant.objects.create(ticket=self.department_ticket, user=self.other_staff)
        self.client.force_login(self.staff)

        response = self.client.get(
            self.url,
            {"scope": "department", "department": str(self.support.id)},
        )

        self.assertIn(self.staff, list(response.context["staff_users"]))
        self.assertNotIn(self.other_staff, list(response.context["staff_users"]))

    def test_assigned_scope_excludes_removed_self_participants(self):
        """Removed-self participants should not appear in assigned-scope results."""
        TicketParticipant.objects.filter(ticket=self.assigned_ticket, user=self.staff).update(
            removed_self=True
        )
        self.client.force_login(self.staff)

        response = self.client.get(self.url, {"scope": "assigned"})
        self.assertNotIn(self.assigned_ticket, response.context["tickets"])

    def test_department_filter_options_include_ticket_department_relations(self):
        """Department options should include departments attached via TicketDepartment."""
        ticket = Ticket.objects.create(
            title="Department relation ticket",
            created_by=self.student,
            status=Ticket.Status.OPEN,
        )
        TicketMessage.objects.create(ticket=ticket, sender=self.student, body="Body")
        TicketDepartment.objects.create(ticket=ticket, department=self.support)

        self.client.force_login(self.student)
        response = self.client.get(self.url)

        self.assertIn(self.support, list(response.context["departments"]))

    def test_department_filter_matches_ticket_department_relations(self):
        """Department filter should include tickets attached via TicketDepartment."""
        ticket = Ticket.objects.create(
            title="Filter by ticket department",
            created_by=self.student,
            status=Ticket.Status.OPEN,
        )
        TicketMessage.objects.create(ticket=ticket, sender=self.student, body="Body")
        TicketDepartment.objects.create(ticket=ticket, department=self.support)

        self.client.force_login(self.student)
        response = self.client.get(self.url, {"department": str(self.support.id)})

        self.assertIn(ticket, response.context["tickets"])
