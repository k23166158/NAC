import uuid as uuid_module
from datetime import timedelta
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from tickets.models import Department, Ticket, TicketAssigned, TicketMessage, TicketParticipant, UserDepartments

User = get_user_model()

class TicketModelTests(TestCase):
    """Test the Ticket model basic fields and methods."""

    def setUp(self):
        """Set up data for the tests."""
        self.user = User.objects.create_user(username='u', password='p', email='e@e.com')
        self.ticket = Ticket.objects.create(title="T", created_by=self.user)

    def test_ticket_creation_defaults_and_str(self):
        """Test creation, defaults, string representation, and relationships."""
        self.assertEqual(self.ticket.status, Ticket.Status.OPEN)
        self.assertIsInstance(self.ticket.uuid, uuid_module.UUID)
        self.assertEqual(str(self.ticket), f"#{self.ticket.id} - {self.ticket.title}")
        self.assertIsNotNone(self.ticket.created_at)
        self.assertEqual(self.user.tickets_created.count(), 1)
        t2 = Ticket.objects.create(title="T2", created_by=self.user)
        self.assertNotEqual(self.ticket.uuid, t2.uuid)

    def test_status_choices(self):
        """Test status choices are correctly defined."""
        self.assertEqual(Ticket.Status.OPEN, 'open')
        self.assertEqual(Ticket.Status.PENDING, 'pending')
        self.assertEqual(Ticket.Status.CLOSED, 'closed')
        t2 = Ticket.objects.create(title="T2", created_by=self.user, status=Ticket.Status.CLOSED)
        self.assertEqual(t2.status, 'closed')


class TicketThreadLogicModelTests(TestCase):
    """Tests for ticket-thread business logic."""

    def setUp(self):
        """Set up users and ticket for thread logic."""
        self.c = User.objects.create_user(username="c", email="c@e.com", password="p")
        self.s = User.objects.create_user(username="s", email="s@e.com", password="p", is_staff=True)
        self.ticket = Ticket.objects.create(title="T", created_by=self.c)

    def test_mark_read_and_touch(self):
        """Test mark_read_for creates/updates and touch updates timestamp."""
        p, created = self.ticket.mark_read_for(self.c)
        self.assertTrue(created)
        first_read = p.last_read_at
        p, created = self.ticket.mark_read_for(self.c)
        self.assertFalse(created)
        self.assertGreater(p.last_read_at, first_read)
        before = self.ticket.updated_at
        self.ticket.touch()
        self.ticket.refresh_from_db()
        self.assertGreater(self.ticket.updated_at, before)

    def test_permissions_and_staff(self):
        """Test staff retrieval, edit permissions, and status closure."""
        TicketParticipant.objects.create(ticket=self.ticket, user=self.s)
        self.assertIn(self.s, self.ticket.get_ticket_staff())
        self.assertTrue(self.ticket.can_edit(self.c))
        other = User.objects.create_user(username="o", email="o@e.com", password="p")
        self.assertFalse(self.ticket.can_edit(other))
        TicketParticipant.objects.create(ticket=self.ticket, user=other, added_by=self.c)
        self.assertTrue(self.ticket.can_edit(other))
        self.assertTrue(self.ticket.close())
        self.assertEqual(self.ticket.status, Ticket.Status.CLOSED)
        self.assertFalse(self.ticket.close())

    def test_department_staff(self):
        """Test department staff retrieval."""
        d = Department.objects.create(name="D", created_by=self.c)
        UserDepartments.objects.create(user=self.s, department=d)
        TicketAssigned.objects.create(ticket=self.ticket, department=d)
        self.assertIn(self.s, self.ticket.get_department_staff())


class TicketHomeDashboardModelTests(TestCase):
    """Tests for home/dashboard query logic."""

    def setUp(self):
        """Setup dashboard fixtures."""
        self.staff = User.objects.create_user(username="st", email="st@e.com", password="p")
        self.t1 = Ticket.objects.create(title="T1", created_by=self.staff, status='open')
        self.t2 = Ticket.objects.create(title="T2", created_by=self.staff, status='closed')

    def test_status_counts_and_scopes(self):
        """Test status counts and base scopes."""
        Ticket.objects.create(title="T3", created_by=self.staff, status='pending')
        counts = Ticket.status_counts()
        self.assertEqual(counts["open"], 1)
        self.assertEqual(counts["closed"], 1)
        self.assertEqual(counts["pending"], 1)
        p_ids = list(Ticket.base_for_scope(self.staff, "personal").values_list("id", flat=True))
        self.assertIn(self.t1.id, p_ids)
        self.assertIsNone(Ticket.base_for_scope(self.staff, "invalid"))
        d_ids = list(Ticket.base_for_scope(self.staff, "department").values_list("id", flat=True))
        self.assertNotIn(self.t1.id, d_ids)

    def test_annotated_and_filters(self):
        """Test annotations and time-based filters."""
        other = User.objects.create_user(username="o", email="o@e.com", password="p")
        TicketMessage.objects.create(ticket=self.t1, sender=other, body="M")
        TicketParticipant.objects.create(ticket=self.t1, user=self.staff)
        
        old = timezone.now() - timedelta(days=8)
        t3 = Ticket.objects.create(title="T3", created_by=self.staff, status='open')
        TicketMessage.objects.create(ticket=t3, sender=self.staff, body="O")
        TicketMessage.objects.filter(ticket=t3).update(edited_at=old, created_at=old)
        
        qs = Ticket.annotated_for_home(self.staff, scope="personal")
        self.assertEqual(qs.get(id=self.t1.id).unread_count, 1)
        self.assertIn(self.t2.id, list(Ticket.completed_from(qs).values_list("id", flat=True)))
        self.assertIn(t3.id, list(Ticket.overdue_from(qs).values_list("id", flat=True)))
        self.assertIn(self.t1.id, list(Ticket.active_from(qs, Ticket.overdue_from(qs)).values_list("id", flat=True)))
        self.assertIsNone(Ticket.annotated_for_home(self.staff, "bad"))