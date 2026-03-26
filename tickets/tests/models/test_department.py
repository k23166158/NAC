from django.contrib.auth import get_user_model
from django.test import TestCase

from tickets.models import Department, UserDepartments, Ticket, TicketAssigned


class DepartmentModelTests(TestCase):
    """Tests for the Department model."""

    def setUp(self):
        """Set up a user for creating departments."""
        self.user = get_user_model().objects.create_user(
            username="creator",
            email="creator@example.com",
            password="pass"
        )

    def test_department_core_behavior(self):
        """Test creation, str, slug, ordering, reverse relations, and cascade delete."""
        dept_b = Department.objects.create(name="B Dept", created_by=self.user)
        dept_a = Department.objects.create(
            name="A Dept", created_by=self.user
        )

        self.assertEqual(str(dept_b), "B Dept")
        self.assertEqual(dept_b.slug, "b-dept")
        self.assertEqual(dept_a.slug, "a-dept")
        self.assertIsNotNone(dept_b.created_on)

        created = list(self.user.departments_created.order_by("name"))
        self.assertEqual(created, [dept_a, dept_b])

        names = list(Department.objects.values_list("name", flat=True))
        self.assertEqual(names, ["A Dept", "B Dept"])

        self.user.delete()
        self.assertEqual(Department.objects.count(), 0)

    def test_delete_for_actor_returns_false_without_permission(self):
        """delete_for_actor should return False and keep the department for unauthorized users."""
        owner = get_user_model().objects.create_user(
            username="owner",
            email="owner@example.com",
            password="pass",
            is_staff=True,
        )
        outsider = get_user_model().objects.create_user(
            username="outsider",
            email="outsider@example.com",
            password="pass",
            is_staff=True,
        )
        department = Department.objects.create(name="Ops", created_by=owner)

        result = department.delete_for_actor(outsider)

        self.assertFalse(result)
        self.assertTrue(Department.objects.filter(pk=department.pk).exists())

    def test_delete_for_actor_deletes_department_for_owner(self):
        """delete_for_actor should delete the department for an authorized owner."""
        owner = get_user_model().objects.create_user(
            username="owner_delete",
            email="owner_delete@example.com",
            password="pass",
            is_staff=True,
        )
        department = Department.objects.create(name="Delete Me", created_by=owner)

        result = department.delete_for_actor(owner)

        self.assertTrue(result)
        self.assertFalse(Department.objects.filter(pk=department.pk).exists())

    def test_get_active_staff_uses_cached_active_assignments_when_present(self):
        """get_active_staff should use prefetched active_assignments when available."""
        active_user = get_user_model().objects.create_user(
            username="active_user",
            email="active@example.com",
            password="pass",
            is_staff=True,
            is_active=True,
        )
        inactive_user = get_user_model().objects.create_user(
            username="inactive_user",
            email="inactive@example.com",
            password="pass",
            is_staff=True,
            is_active=False,
        )
        department = Department.objects.create(name="Support", created_by=self.user)
        active_assignment = UserDepartments.objects.create(user=active_user, department=department)
        UserDepartments.objects.create(user=inactive_user, department=department)
        department.active_assignments = [active_assignment]

        active_staff = department.get_active_staff()

        self.assertEqual(active_staff, [active_user])

    def test_assign_member_creates_membership_and_returns_self(self):
        """assign_member should create a department membership and return the department."""
        staff_user = get_user_model().objects.create_user(
            username="staff_user",
            email="staff@example.com",
            password="pass",
            is_staff=True,
        )
        department = Department.objects.create(name="Admissions", created_by=self.user)

        result = department.assign_member(staff_user)

        self.assertEqual(result, department)
        self.assertTrue(
            UserDepartments.objects.filter(user=staff_user, department=department).exists()
        )

    def test_assigned_to_user_with_ticket_counts_filters_and_annotates(self):
        """assigned_to_user_with_ticket_counts should return only assigned departments with ticket counts."""
        staff_user, gamma = self._build_assigned_department_queryset_fixture()

        departments = list(
            Department.assigned_to_user_with_ticket_counts(staff_user, search_query="Match")
        )

        self._assert_assigned_department_queryset(departments, gamma)

    def _build_assigned_department_queryset_fixture(self):
        """Create departments, memberships, and tickets for assigned department queryset tests."""
        staff_user = get_user_model().objects.create_user(
            username="assigned_staff",
            email="assigned_staff@example.com",
            password="pass",
            is_staff=True,
        )
        other_staff = get_user_model().objects.create_user(
            username="other_staff",
            email="other_staff@example.com",
            password="pass",
            is_staff=True,
        )
        alpha, beta, gamma = self._create_department_queryset_departments()
        UserDepartments.objects.create(user=staff_user, department=alpha)
        UserDepartments.objects.create(user=staff_user, department=gamma)
        UserDepartments.objects.create(user=other_staff, department=beta)
        self._create_department_queryset_tickets(gamma)
        return staff_user, gamma

    def _create_department_queryset_departments(self):
        """Create departments for assigned department queryset tests."""
        alpha = Department.objects.create(
            name="Alpha Team",
            description="Primary support",
            created_by=self.user,
        )
        beta = Department.objects.create(
            name="Beta Team",
            description="Secondary support",
            created_by=self.user,
        )
        gamma = Department.objects.create(
            name="Gamma Team",
            description="Match this",
            created_by=self.user,
        )
        return alpha, beta, gamma

    def _create_department_queryset_tickets(self, department):
        """Create open and closed tickets for the provided department."""
        open_ticket = Ticket.objects.create(
            title="Open",
            created_by=self.user,
            status=Ticket.Status.OPEN,
        )
        closed_ticket = Ticket.objects.create(
            title="Closed",
            created_by=self.user,
            status=Ticket.Status.CLOSED,
        )
        TicketAssigned.objects.create(ticket=open_ticket, department=department)
        TicketAssigned.objects.create(ticket=closed_ticket, department=department)

    def _assert_assigned_department_queryset(self, departments, expected_department):
        """Assert assigned department queryset filtering and ticket count annotations."""
        self.assertEqual([department.name for department in departments], [expected_department.name])
        self.assertEqual(departments[0].active_ticket_count, 1)
        self.assertEqual(departments[0].completed_ticket_count, 1)
