import uuid as uuid_module
from datetime import timedelta

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone

from tickets.models import (
    Department,
    Ticket,
    TicketAssigned,
    TicketMessage,
    TicketParticipant,
    UserDepartments,
)

User = get_user_model()

class TicketModelTests(TestCase):
    """Test the Ticket model."""
    def setUp(self):
        """
        Set up data for the tests. 
        This runs before every single test method.
        """
        self.user = User.objects.create_user(
            username='testuser', 
            password='testpassword123',
            email='test@example.com',
            first_name='Test',
            last_name='User'
        )
        
        self.ticket = Ticket.objects.create(
            title="Test Server Issue",
            created_by=self.user
        )

    def test_ticket_creation_and_defaults(self):
        """Test that a ticket is created with the correct default values."""
        self.assertTrue(isinstance(self.ticket, Ticket))
        self.assertEqual(self.ticket.title, "Test Server Issue")
        self.assertEqual(self.ticket.created_by, self.user)
        self.assertEqual(self.ticket.status, Ticket.Status.OPEN)
        self.assertIsNotNone(self.ticket.uuid)
        self.assertIsInstance(self.ticket.uuid, uuid_module.UUID)

    def test_str_representation(self):
        """Test the __str__ method matches the format '#{id} - {title}'."""
        string_representation = str(self.ticket)
        expected_format = f"#{self.ticket.id} - {self.ticket.title}"
        self.assertEqual(string_representation, expected_format)

    def test_status_choices(self):
        """Test that the Status TextChoices are correctly defined."""
        self.assertEqual(Ticket.Status.OPEN, 'open')
        self.assertEqual(Ticket.Status.PENDING, 'pending')
        self.assertEqual(Ticket.Status.CLOSED, 'closed')
        
        closed_ticket = Ticket.objects.create(
            title="Closed Ticket",
            created_by=self.user,
            status=Ticket.Status.CLOSED
        )
        self.assertEqual(closed_ticket.status, 'closed')

    def test_timestamps(self):
        """Test that created_at and updated_at are automatically set."""
        self.assertIsNotNone(self.ticket.created_at)
        self.assertIsNotNone(self.ticket.updated_at)
        
    def test_user_relationship(self):
        """Test the 'related_name' attribute allows reverse lookup."""
        user_tickets = self.user.tickets_created.all()
        
        self.assertIn(self.ticket, user_tickets)
        self.assertEqual(user_tickets.count(), 1)

    def test_ticket_uuid_is_unique(self):
        """Test that each ticket gets a unique uuid."""
        another_ticket = Ticket.objects.create(
            title="Another Ticket",
            created_by=self.user,
        )
        self.assertNotEqual(self.ticket.uuid, another_ticket.uuid)
        self.assertEqual(
            Ticket.objects.filter(uuid=self.ticket.uuid).count(),
            1,
        )


class TicketThreadLogicModelTests(TestCase):
    """Tests for ticket-thread business logic extracted to Ticket model."""

    def setUp(self):
        """Create common users/ticket data for thread-model logic tests."""
        self.creator = self._mk_user("creator", "Creator")
        self.staff = self._mk_user("staff", "Staff", is_staff=True)
        self.other = self._mk_user("other", "Other")
        self.superuser = self._mk_user("admin", "Admin", is_superuser=True)
        self.ticket = Ticket.objects.create(title="Thread logic ticket", created_by=self.creator)

    def _mk_user(self, username, first_name, **extra):
        """Create a test user with consistent defaults."""
        return User.objects.create_user(
            username=username,
            password="password123",
            email=f"{username}@example.com",
            first_name=first_name,
            last_name="User",
            **extra,
        )

    def test_mark_read_for_create_and_update(self):
        """mark_read_for should create and then update a participant row."""
        participant, created = self.ticket.mark_read_for(self.creator)
        self.assertTrue(created)
        self.assertIsNotNone(participant.last_read_at)

        first_read = participant.last_read_at
        participant, created = self.ticket.mark_read_for(self.creator)
        self.assertFalse(created)
        self.assertGreater(participant.last_read_at, first_read)

    def test_touch_updates_updated_at(self):
        """touch should update updated_at."""
        before = self.ticket.updated_at
        self.ticket.touch()
        self.ticket.refresh_from_db()
        self.assertGreater(self.ticket.updated_at, before)

    def test_get_ticket_staff_returns_participant_users(self):
        """get_ticket_staff should return users on ticket participants."""
        TicketParticipant.objects.create(ticket=self.ticket, user=self.staff, added_by=self.creator)
        users = self.ticket.get_ticket_staff()
        self.assertIn(self.staff, users)

    def test_get_department_staff_returns_department_assigned_staff(self):
        """get_department_staff should include users from assigned ticket departments."""
        department = Department.objects.create(name="Ops", created_by=self.creator)
        UserDepartments.objects.create(user=self.staff, department=department)
        TicketAssigned.objects.create(ticket=self.ticket, department=department)
        self.assertIn(self.staff, self.ticket.get_department_staff())

    def test_can_edit_paths_and_false_case(self):
        """can_edit should allow superuser/creator/participant/dept-staff and deny others."""
        self.assertTrue(self.ticket.can_edit(self.superuser))
        self.assertTrue(self.ticket.can_edit(self.creator))

        self.assertFalse(self.ticket.can_edit(self.other))

        TicketParticipant.objects.create(ticket=self.ticket, user=self.other, added_by=self.creator)
        self.assertTrue(self.ticket.can_edit(self.other))

        another = User.objects.create_user(
            username="deptstaff",
            password="password123",
            email="deptstaff@example.com",
            first_name="Dept",
            last_name="Staff",
            is_staff=True,
        )
        department = Department.objects.create(name="Support", created_by=self.creator)
        UserDepartments.objects.create(user=another, department=department)
        TicketAssigned.objects.create(ticket=self.ticket, department=department)
        self.assertTrue(self.ticket.can_edit(another))

    def test_close_changes_status_once(self):
        """close should close open ticket then return False if already closed."""
        self.assertTrue(self.ticket.close())
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.status, Ticket.Status.CLOSED)
        self.assertFalse(self.ticket.close())


class TicketHomeDashboardModelTests(TestCase):
    """Tests for home/dashboard query logic moved into Ticket model."""

    def setUp(self):
        """Create users/tickets/messages for home query model methods."""
        self.student = self._mk_user("home_student", "Home", "Student")
        self.staff = self._mk_user("home_staff", "Home", "Staff", is_staff=True)
        self.other_staff = self._mk_user("home_other_staff", "Other", "Staff", is_staff=True)
        self._build_ticket_fixtures()
        self._build_department_fixtures()

    def _mk_user(self, username, first_name, last_name, **extra):
        """Create a dashboard test user."""
        return User.objects.create_user(
            username=username,
            password="password123",
            email=f"{username}@example.com",
            first_name=first_name,
            last_name=last_name,
            **extra,
        )

    def _build_ticket_fixtures(self):
        """Create ticket fixtures used across dashboard tests."""
        self.personal_open = Ticket.objects.create(title="Personal Open", created_by=self.staff, status=Ticket.Status.OPEN)
        self.personal_closed = Ticket.objects.create(title="Personal Closed", created_by=self.staff, status=Ticket.Status.CLOSED)
        self.foreign_open = Ticket.objects.create(title="Foreign Open", created_by=self.student, status=Ticket.Status.OPEN)
        self.assigned_only = Ticket.objects.create(title="Assigned Only", created_by=self.student, status=Ticket.Status.PENDING)
        TicketParticipant.objects.create(ticket=self.assigned_only, user=self.staff)

    def _build_department_fixtures(self):
        """Create department assignment fixtures for department-scope tests."""
        self.department = Department.objects.create(name="HomeDept", created_by=self.staff)
        UserDepartments.objects.create(user=self.staff, department=self.department)
        TicketAssigned.objects.create(ticket=self.foreign_open, department=self.department)

    def test_status_counts(self):
        """status_counts should return open/pending/closed totals."""
        counts = Ticket.status_counts()
        self.assertEqual(counts["open"], 2)
        self.assertEqual(counts["pending"], 1)
        self.assertEqual(counts["closed"], 1)

    def test_base_for_scope_personal_department_assigned_and_invalid(self):
        """base_for_scope should return expected queryset per scope and None for invalid."""
        personal_ids = list(Ticket.base_for_scope(self.staff, "personal").values_list("id", flat=True))
        department_ids = list(Ticket.base_for_scope(self.staff, "department").values_list("id", flat=True))
        assigned_ids = list(Ticket.base_for_scope(self.staff, "assigned").values_list("id", flat=True))

        self.assertIn(self.personal_open.id, personal_ids)
        self.assertIn(self.personal_closed.id, personal_ids)
        self.assertNotIn(self.foreign_open.id, personal_ids)

        self.assertIn(self.foreign_open.id, department_ids)
        self.assertNotIn(self.personal_open.id, department_ids)

        self.assertIn(self.assigned_only.id, assigned_ids)
        self.assertIsNone(Ticket.base_for_scope(self.staff, "invalid"))

    def test_annotated_for_home_adds_last_message_fields_and_unread_count(self):
        """annotated_for_home should annotate last message + unread count fields."""
        first = TicketMessage.objects.create(
            ticket=self.personal_open,
            sender=self.student,
            body="Old update",
        )
        second = TicketMessage.objects.create(
            ticket=self.personal_open,
            sender=self.other_staff,
            body="Latest update",
        )
        TicketParticipant.objects.create(ticket=self.personal_open, user=self.staff)

        qs = Ticket.annotated_for_home(self.staff, scope="personal")
        ticket = qs.get(id=self.personal_open.id)

        self.assertEqual(ticket.last_message_body, "Latest update")
        self.assertEqual(ticket.last_message_sender_id, self.other_staff.id)
        self.assertEqual(ticket.last_sender_first, self.other_staff.first_name)
        self.assertEqual(ticket.last_sender_last, self.other_staff.last_name)
        self.assertTrue(hasattr(ticket, "unread_count"))
        self.assertEqual(ticket.unread_count, 2)
        self.assertLess(first.edited_at, second.edited_at)

    def test_annotated_for_home_invalid_scope_returns_none(self):
        """annotated_for_home should return None for invalid scope."""
        self.assertIsNone(Ticket.annotated_for_home(self.staff, scope="bad_scope"))

    def test_private_annotation_helpers_are_callable(self):
        """Private annotation helpers should return querysets with expected fields."""
        TicketMessage.objects.create(
            ticket=self.personal_open,
            sender=self.student,
            body="Hello",
        )
        base = Ticket.base_for_scope(self.staff, "personal")
        with_last = Ticket._annotate_last_message_for_user(base, self.staff)
        with_unread = Ticket._annotate_unread_count_for_user(with_last, self.staff)
        row = with_unread.get(id=self.personal_open.id)
        self.assertTrue(hasattr(row, "last_message_at"))
        self.assertTrue(hasattr(row, "user_last_read_at"))
        self.assertTrue(hasattr(row, "unread_count"))

    def test_completed_overdue_and_active_from(self):
        """completed_from/overdue_from/active_from should partition dashboard tickets."""
        overdue_ticket = self._create_overdue_ticket()
        recent_ticket = self._create_recent_ticket()
        completed_ids, overdue_ids, active_ids = self._dashboard_partition_ids()
        self.assertIn(self.personal_closed.id, completed_ids)
        self.assertIn(overdue_ticket.id, overdue_ids)
        self.assertIn(recent_ticket.id, active_ids)
        self.assertNotIn(overdue_ticket.id, active_ids)

    def _create_overdue_ticket(self):
        """Create a ticket with an old user-authored latest message."""
        overdue_ticket = Ticket.objects.create(title="Overdue", created_by=self.staff, status=Ticket.Status.OPEN)
        overdue_msg = TicketMessage.objects.create(ticket=overdue_ticket, sender=self.student, body="Old user message")
        old_time = timezone.now() - timedelta(days=8)
        TicketMessage.objects.filter(pk=overdue_msg.pk).update(edited_at=old_time, created_at=old_time)
        return overdue_ticket

    def _create_recent_ticket(self):
        """Create a ticket with a recent message."""
        recent_ticket = Ticket.objects.create(title="Recent", created_by=self.staff, status=Ticket.Status.OPEN)
        TicketMessage.objects.create(ticket=recent_ticket, sender=self.student, body="Recent message")
        return recent_ticket

    def _dashboard_partition_ids(self):
        """Return IDs for completed, overdue, and active dashboard slices."""
        qs = Ticket.annotated_for_home(self.staff, "personal")
        completed = Ticket.completed_from(qs)
        overdue = Ticket.overdue_from(qs)
        active = Ticket.active_from(qs, overdue)
        return (
            list(completed.values_list("id", flat=True)),
            list(overdue.values_list("id", flat=True)),
            list(active.values_list("id", flat=True)),
        )
