from django.test import TestCase
from django.contrib.auth import get_user_model
from unittest import mock
from tickets.helpers.ticket_assignment import assign_staff_to_ticket, assign_department_to_ticket, _restore_participant
from tickets.models import Ticket, TicketParticipant, TicketMessage, TicketDepartment, Department
from tickets.models.notification import Notification

User = get_user_model()

class AssignStaffToTicketTests(TestCase):
    """Test cases for assign_staff_to_ticket helper function."""

    def setUp(self):
        """Create test data."""
        self.s = User.objects.create_user(username='s', email='s@e.com', password='p', first_name='A', last_name='B')
        self.a = User.objects.create_user(username='a', email='a@e.com', password='p')
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

    @mock.patch("tickets.helpers.ticket_assignment.create_notification")
    def test_assign_staff_creates_staff_assigned_notification(self, mock_create):
        """Assigning staff should create a STAFF_ASSIGNED notification."""
        assign_staff_to_ticket(self.ticket, self.s, added_by=self.a)
        mock_create.assert_called_once_with(
            user=self.s,
            actor=self.a,
            notification_type=Notification.NotificationType.STAFF_ASSIGNED,
            link=f"/tickets/{self.ticket.uuid}/",
            target_object=self.ticket,
        )

    @mock.patch("tickets.helpers.ticket_assignment.create_notification")
    def test_assign_existing_staff_does_not_notify(self, mock_create):
        """Assigning staff who is already a participant should not create a notification."""
        TicketParticipant.objects.create(ticket=self.ticket, user=self.s)
        assign_staff_to_ticket(self.ticket, self.s, added_by=self.a)
        mock_create.assert_not_called()

class AssignDepartmentToTicketTests(TestCase):
    """Test cases for assign_department_to_ticket helper function."""

    def setUp(self):
        """Set up test department and ticket."""
        self.c = User.objects.create_user(username="c", email="c@e.com", password="p", first_name="C")
        self.s1 = User.objects.create_user(username="s1", email="s1@e.com", password="p")
        self.s2 = User.objects.create_user(username="s2", email="s2@e.com", password="p")
        self.ticket = Ticket.objects.create(title="T", created_by=self.c)
        self.dept = Department.objects.create(name="D", created_by=self.c)
        self.dept.members.add(self.c, self.s1, self.s2)

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

    @mock.patch("tickets.helpers.ticket_assignment.create_notification")
    def test_assign_department_creates_dept_assigned_notifications(self, mock_create):
        """Assigning a department should create DEPT_ASSIGNED notifications for each member (except actor)."""
        assign_department_to_ticket(self.ticket, self.dept, added_by=self.c)
        calls = mock_create.call_args_list
        notified_users = [c.kwargs["user"] for c in calls]
        self.assertIn(self.s1, notified_users)
        self.assertIn(self.s2, notified_users)
        self.assertNotIn(self.c, notified_users)
        for call in calls:
            self.assertEqual(
                call.kwargs["notification_type"],
                Notification.NotificationType.DEPT_ASSIGNED,
            )

    @mock.patch("tickets.helpers.ticket_assignment.create_notification")
    def test_assign_department_actor_member_not_notified(self, mock_create):
        """When the actor is a department member, they should not receive a notification."""
        assign_department_to_ticket(self.ticket, self.dept, added_by=self.c)
        notified_users = [c.kwargs["user"] for c in mock_create.call_args_list]
        self.assertNotIn(self.c, notified_users)

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
