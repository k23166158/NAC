import uuid as uuid_module
from datetime import timedelta
from unittest.mock import patch
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

    def test_create_with_initial_message_allows_empty_departments(self):
        """create_with_initial_message should create ticket/message when no departments are selected."""
        cleaned_data = {
            "title": "No departments",
            "body": "Body text",
            "departments": [],
        }

        ticket = Ticket.create_with_initial_message(
            creator=self.user,
            cleaned_data=cleaned_data,
            files=None,
        )

        self.assertEqual(ticket.title, "No departments")
        self.assertEqual(ticket.created_by, self.user)
        self.assertTrue(Ticket.objects.filter(id=ticket.id).exists())
        self.assertEqual(TicketMessage.objects.filter(ticket=ticket).count(), 1)
        self.assertEqual(TicketAssigned.objects.filter(ticket=ticket).count(), 0)


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

    def test_admin_ticket_stats(self):
        """admin_ticket_stats should include total and grouped status counts."""
        Ticket.objects.create(title="T3", created_by=self.staff, status='pending')

        stats = Ticket.admin_ticket_stats()

        self.assertEqual(stats["total"], 3)
        self.assertEqual(stats["open"], 1)
        self.assertEqual(stats["pending"], 1)
        self.assertEqual(stats["closed"], 1)

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

    def test_search_page_queryset_returns_none_queryset_fallback(self):
        """search_page_queryset returns an empty queryset when base scope is None."""
        with patch.object(Ticket, "base_for_scope", return_value=None):
            qs = Ticket.search_page_queryset(self.staff, {"scope": "personal"})
        self.assertEqual(qs.count(), 0)

    def test_search_page_queryset_applies_annotations_and_filters(self):
        """search_page_queryset should apply the full search pipeline."""
        TicketMessage.objects.create(ticket=self.t1, sender=self.staff, body="Alpha body")
        filters = {
            "scope": "personal",
            "q": "Alpha",
            "status": Ticket.Status.OPEN,
            "department": "",
            "assigned_staff": "",
            "created_from": (timezone.now() - timedelta(days=1)).date().isoformat(),
            "created_to": (timezone.now() + timedelta(days=1)).date().isoformat(),
        }

        queryset = Ticket.search_page_queryset(self.staff, filters)

        self.assertEqual(list(queryset), [self.t1])

    def test_search_filter_options_returns_empty_when_scope_has_no_queryset(self):
        """search_filter_options returns empty options when base scope is None."""
        with patch.object(Ticket, "base_for_scope", return_value=None):
            options = Ticket.search_filter_options(self.staff, "personal")
        self.assertEqual(options, {"departments": [], "staff_users": []})

    def test_created_date_filters_apply_bounds(self):
        """Created date filters should apply lower and upper bounds."""
        older = timezone.now() - timedelta(days=3)
        Ticket.objects.filter(pk=self.t1.pk).update(created_at=older)
        queryset = Ticket.objects.all()

        filtered_from = Ticket._filter_created_from(
            queryset,
            (timezone.now() - timedelta(days=1)).date().isoformat(),
        )
        filtered_to = Ticket._filter_created_to(
            queryset,
            (timezone.now() - timedelta(days=2)).date().isoformat(),
        )

        self.assertNotIn(self.t1, filtered_from)
        self.assertIn(self.t1, filtered_to)
