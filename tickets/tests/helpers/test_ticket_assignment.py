from django.test import TestCase
from django.contrib.auth import get_user_model
from unittest import mock
from tickets.helpers.ticket_assignment import assign_staff_to_ticket, assign_department_to_ticket, _restore_participant
from tickets.models import Ticket, TicketParticipant, TicketMessage, TicketDepartment, Department

User = get_user_model()

class AssignStaffToTicketTests(TestCase):
    """Test cases for assign_staff_to_ticket helper function."""

    def setUp(self):
        """Create test data."""
        self.s = User.objects.create_user(username='s', email='s@e.com', password='p', first_name='A', last_name='B')
        self.ticket = Ticket.objects.create(title="T", created_by=self.s)

    def test_assign_staff_creates_and_restores(self):
        """Test staff assignment creates participant, restores if removed, updates ticket."""
        self.assertTrue(assign_staff_to_ticket(self.ticket, self.s))
        self.assertTrue(TicketParticipant.objects.filter(ticket=self.ticket, user=self.s).exists())
        self.assertEqual(TicketMessage.objects.count(), 1)
        self.assertFalse(assign_staff_to_ticket(self.ticket, self.s))
        p = TicketParticipant.objects.get(ticket=self.ticket, user=self.s)
        p.removed_self = True
        p.save()
        self.assertFalse(assign_staff_to_ticket(self.ticket, self.s))
        p.refresh_from_db()
        self.assertFalse(p.removed_self)

    @mock.patch('tickets.helpers.ticket_assignment.TicketParticipant')
    def test_assign_staff_added_by_logic(self, MockPart):
        """Test added_by logic handles missing model fields safely."""
        del MockPart.added_by
        MockPart.objects.get_or_create.return_value = (mock.Mock(), True)
        assign_staff_to_ticket(self.ticket, self.s, added_by=self.s)
        kwargs = MockPart.objects.get_or_create.call_args[1]
        self.assertEqual(kwargs['defaults'], {})
        assign_staff_to_ticket(self.ticket, self.s, added_by=None)
        kwargs_empty = MockPart.objects.get_or_create.call_args[1]
        self.assertEqual(kwargs_empty['defaults'], {})

class AssignDepartmentToTicketTests(TestCase):
    """Test cases for assign_department_to_ticket helper function."""

    def setUp(self):
        """Set up test department and ticket."""
        self.c = User.objects.create_user(username="c", email="c@e.com", password="p", first_name="C")
        self.ticket = Ticket.objects.create(title="T", created_by=self.c)
        self.dept = Department.objects.create(name="D", created_by=self.c)
        self.dept.members.add(self.c)

    def test_assign_department_logic(self):
        """Test department assignment links members, avoids duplicates, restores members."""
        assign_department_to_ticket(self.ticket, self.dept, added_by=self.c)
        self.assertTrue(TicketDepartment.objects.filter(ticket=self.ticket, department=self.dept).exists())
        self.assertTrue(TicketParticipant.objects.filter(ticket=self.ticket, user=self.c).exists())
        self.assertEqual(TicketMessage.objects.count(), 1)
        p = TicketParticipant.objects.get(ticket=self.ticket, user=self.c)
        p.removed_self = True
        p.save()
        assign_department_to_ticket(self.ticket, self.dept, added_by=self.c)
        p.refresh_from_db()
        self.assertFalse(p.removed_self)
        self.assertEqual(TicketParticipant.objects.filter(ticket=self.ticket, user=self.c).count(), 1)

class RestoreParticipantTests(TestCase):
    """Test cases for _restore_participant helper function."""
    def test_restore_participant_logic(self):
        """Test restoring participant flips removed_self flag."""
        c = User.objects.create_user(username='c2', email='c2@e.com', password='p')
        t = Ticket.objects.create(title="T", created_by=c)
        p = TicketParticipant.objects.create(ticket=t, user=c, removed_self=True)
        _restore_participant(p)
        p.refresh_from_db()
        self.assertFalse(p.removed_self)
        _restore_participant(p)
        p.refresh_from_db()
        self.assertFalse(p.removed_self)