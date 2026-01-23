from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from tickets.models import Department


class DepartmentModelTests(TestCase):
    """Tests for the Department model."""

    def setUp(self):
        """Set up a user for creating departments."""
        User = get_user_model()
        self.user = User.objects.create_user(
            username="creator",
            email="creator@example.com",
            password="pass12345",
        )

    def test_create_department_persists_fields(self):
        """Test that creating a Department saves all fields correctly."""
        dept = Department.objects.create(name="IT Support", created_by=self.user)

        self.assertIsNotNone(dept.id)
        self.assertEqual(dept.name, "IT Support")
        self.assertEqual(dept.created_by, self.user)
        self.assertIsNotNone(dept.created_on)

    def test_created_on_is_set_close_to_now(self):
        """Test that created_on is set to the current time on creation."""
        before = timezone.now()
        dept = Department.objects.create(name="Registry", created_by=self.user)
        after = timezone.now()

        self.assertGreaterEqual(dept.created_on, before)
        self.assertLessEqual(dept.created_on, after)

    def test_str_returns_name(self):
        """Test that the string representation of Department is its name."""
        dept = Department.objects.create(name="Finance", created_by=self.user)
        self.assertEqual(str(dept), "Finance")

    def test_reverse_relation_from_user_works(self):
        """Test that we can access departments created by a user via reverse relation."""
        d1 = Department.objects.create(name="A", created_by=self.user)
        d2 = Department.objects.create(name="B", created_by=self.user)

        created = list(self.user.departments_created.order_by("name"))
        self.assertEqual(created, [d1, d2])

    def test_ordering_meta_sorts_by_name(self):
        """Test that the Department model orders by name as per Meta options."""
        Department.objects.create(name="Zeta", created_by=self.user)
        Department.objects.create(name="Alpha", created_by=self.user)
        Department.objects.create(name="Beta", created_by=self.user)

        names = list(Department.objects.values_list("name", flat=True))
        self.assertEqual(names, ["Alpha", "Beta", "Zeta"])

    def test_cascade_delete_user_deletes_department(self):
        """Test that deleting the user also deletes their created departments."""
        Department.objects.create(name="Ops", created_by=self.user)
        self.user.delete()

        self.assertEqual(Department.objects.count(), 0)