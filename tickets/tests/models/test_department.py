from django.contrib.auth import get_user_model
from django.test import TestCase

from tickets.models import Department, UserDepartments


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
