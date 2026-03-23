"""Tests for the DepartmentInvitation model."""
from django.contrib.auth import get_user_model
from django.test import TestCase

from tickets.models import Department, DepartmentInvitation

User = get_user_model()


class DepartmentInvitationModelTests(TestCase):
    """Tests for the DepartmentInvitation model."""

    def setUp(self):
        """Set up users and a department."""
        self.sender = User.objects.create_user(
            username="sender",
            email="sender@example.com",
            password="pw",
            is_staff=True,
        )
        self.recipient = User.objects.create_user(
            username="recipient",
            email="recipient@example.com",
            password="pw",
            is_staff=True,
        )
        self.department = Department.objects.create(
            name="IT",
            created_by=self.sender,
        )

    def test_create_invitation_persists_fields(self):
        """Test that creating an invitation saves all fields."""
        inv = DepartmentInvitation.objects.create(
            sender=self.sender,
            recipient=self.recipient,
            department=self.department,
            status='pending',
        )
        self.assertIsNotNone(inv.id)
        self.assertEqual(inv.sender, self.sender)
        self.assertEqual(inv.recipient, self.recipient)
        self.assertEqual(inv.department, self.department)
        self.assertEqual(inv.status, 'pending')
        self.assertIsNotNone(inv.created_at)

    def test_str_returns_expected_format(self):
        """Test that __str__ returns invite description."""
        inv = DepartmentInvitation.objects.create(
            sender=self.sender,
            recipient=self.recipient,
            department=self.department,
        )
        self.assertEqual(
            str(inv),
            f"Invite: {self.department.name} -> {self.recipient.username} (pending)",
        )

    def test_ordering_meta_sorts_by_created_at_desc(self):
        """Test that Meta ordering is by -created_at."""
        inv1 = DepartmentInvitation.objects.create(
            sender=self.sender,
            recipient=self.recipient,
            department=self.department,
        )
        inv2 = DepartmentInvitation.objects.create(
            sender=self.sender,
            recipient=self.recipient,
            department=Department.objects.create(name="HR", created_by=self.sender),
        )
        ordered = list(DepartmentInvitation.objects.all())
        self.assertEqual(ordered, [inv2, inv1])
