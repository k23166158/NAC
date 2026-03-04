from django.contrib.auth import get_user_model
from django.test import TestCase

from tickets.models import Department, Ticket, TicketMessage, TicketParticipant
from tickets.models.ticket_department import TicketDepartment

User = get_user_model()


class TicketDepartmentModelTests(TestCase):
    """Tests for TicketDepartment helper methods."""

    def setUp(self):
        """Create users/ticket/department fixtures."""
        self.creator = User.objects.create_user(
            username="dept_creator",
            password="password123",
            email="dept_creator@example.com",
            first_name="Dept",
            last_name="Creator",
            is_staff=True,
        )
        self.staff = User.objects.create_user(
            username="dept_staff",
            password="password123",
            email="dept_staff@example.com",
            first_name="Dept",
            last_name="Staff",
            is_staff=True,
        )
        self.ticket = Ticket.objects.create(title="Dept ticket", created_by=self.creator)
        self.department = Department.objects.create(name="Support Dept", created_by=self.creator)
        self.department.members.add(self.staff)

    def test_assign_department_creates_mapping_and_side_effects(self):
        """assign_department should create relation, participants, and log message."""
        TicketDepartment.assign_department(self.ticket, self.department, added_by=self.creator)
        self.assertTrue(
            TicketDepartment.objects.filter(ticket=self.ticket, department=self.department).exists()
        )
        self.assertTrue(
            TicketParticipant.objects.filter(ticket=self.ticket, user=self.staff).exists()
        )
        self.assertTrue(
            TicketMessage.objects.filter(
                ticket=self.ticket,
                body__contains=self.department.name,
                sender=None,
            ).exists()
        )

    def test_remove_department_deletes_mapping_and_logs(self):
        """remove_department should delete mapping and add system message."""
        TicketDepartment.objects.create(ticket=self.ticket, department=self.department)
        TicketDepartment.remove_department(self.ticket, self.department)
        self.assertFalse(
            TicketDepartment.objects.filter(ticket=self.ticket, department=self.department).exists()
        )
        self.assertTrue(
            TicketMessage.objects.filter(
                ticket=self.ticket,
                body__contains=f"{self.department.name} was removed from the ticket.",
                sender=None,
            ).exists()
        )
