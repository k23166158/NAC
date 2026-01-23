from django.test import TestCase
from django.contrib.auth import get_user_model
from django.db.utils import IntegrityError
from tickets.models import Ticket, Department, TicketAssigned

User = get_user_model()

class TicketAssignedModelTests(TestCase):
    """Tests for the TicketAssigned model."""

    def setUp(self):
        """Set up the dependencies: A User, A Ticket, and A Department."""
        self.user = User.objects.create_user(
            username='assignuser', 
            password='password123',
            email='assign@example.com',
            first_name='Assign',
            last_name='Tester'
        )
        
        self.ticket = Ticket.objects.create(
            title="Printer Issue",
            created_by=self.user
        )

        self.department = Department.objects.create(
            name="IT Support",
            created_by=self.user
        )

    def test_assignment_creation(self):
        """Test that we can successfully link a ticket to a department."""
        assignment = TicketAssigned.objects.create(
            ticket=self.ticket,
            department=self.department
        )
        

        self.assertIsNotNone(assignment.id)
        self.assertEqual(assignment.ticket, self.ticket)
        self.assertEqual(assignment.department, self.department)

    def test_str_representation(self):
        """Test the string representation matches the format."""
        assignment = TicketAssigned.objects.create(
            ticket=self.ticket,
            department=self.department
        )
        expected_str = f"Assignment: Ticket #{self.ticket.id} -> {self.department.name}"
        self.assertEqual(str(assignment), expected_str)

    def test_unique_constraint(self):
        """Test that assigning the same ticket to the same department twice fails."""
        TicketAssigned.objects.create(
            ticket=self.ticket,
            department=self.department
        )

        with self.assertRaises(IntegrityError):
            TicketAssigned.objects.create(
                ticket=self.ticket,
                department=self.department
            )

    def test_ticket_deletion_cascades(self):
        """Test that deleting a Ticket also deletes the assignment."""
        TicketAssigned.objects.create(
            ticket=self.ticket,
            department=self.department
        )
        
        self.ticket.delete()
        
        self.assertEqual(TicketAssigned.objects.count(), 0)

    def test_department_deletion_cascades(self):
        """Test that deleting a Department also deletes the assignment."""
        TicketAssigned.objects.create(
            ticket=self.ticket,
            department=self.department
        )
        self.department.delete()
        self.assertEqual(TicketAssigned.objects.count(), 0)

    def test_related_names(self):
        """Test that we can access assignments from both Ticket and Department sides."""
        assignment = TicketAssigned.objects.create(
            ticket=self.ticket,
            department=self.department
        )
        self.assertIn(assignment, self.ticket.assignments.all())
        self.assertIn(assignment, self.department.assigned_tickets.all())