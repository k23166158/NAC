from django.contrib.auth import get_user_model
from django.test import TestCase

from tickets.models import Department


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