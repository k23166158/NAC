from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model

from tickets.models import Department, UserDepartments, Ticket, TicketAssigned

User = get_user_model()


class DepartmentActiveTicketsViewTests(TestCase):
    """Tests for the DepartmentActiveTicketsView."""

    def setUp(self):
        self.owner = User.objects.create_user(username="o", email="o@e.com", password="p", is_staff=True)
        self.mem = User.objects.create_user(username="m", email="m@e.com", password="p")
        self.out = User.objects.create_user(username="out", email="out@e.com", password="p")
        self.dept = Department.objects.create(name="IT", created_by=self.owner)
        UserDepartments.objects.create(user=self.mem, department=self.dept)
        UserDepartments.objects.create(user=self.owner, department=self.dept)
        self.url = reverse("department_active_tickets", kwargs={"department_slug": self.dept.slug})

    def test_non_member_gets_403(self):
        self.client.force_login(self.out)
        self.assertEqual(self.client.get(self.url).status_code, 403)

    def test_unauthenticated_redirects_to_login(self):
        res = self.client.get(self.url)
        self.assertEqual(res.status_code, 302)

    def test_member_sees_active_tickets(self):
        t_open = Ticket.objects.create(title="Open", created_by=self.mem, status=Ticket.Status.OPEN)
        t_pending = Ticket.objects.create(title="Pending", created_by=self.mem, status=Ticket.Status.PENDING)
        t_closed = Ticket.objects.create(title="Closed", created_by=self.mem, status=Ticket.Status.CLOSED)
        TicketAssigned.objects.create(ticket=t_open, department=self.dept)
        TicketAssigned.objects.create(ticket=t_pending, department=self.dept)
        TicketAssigned.objects.create(ticket=t_closed, department=self.dept)

        self.client.force_login(self.mem)
        res = self.client.get(self.url)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.context["page"].paginator.count, 2)

    def test_empty_state(self):
        self.client.force_login(self.mem)
        res = self.client.get(self.url)
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "No active tickets found.")


class DepartmentClosedTicketsViewTests(TestCase):
    """Tests for the DepartmentClosedTicketsView."""

    def setUp(self):
        self.owner = User.objects.create_user(username="o", email="o@e.com", password="p", is_staff=True)
        self.mem = User.objects.create_user(username="m", email="m@e.com", password="p")
        self.out = User.objects.create_user(username="out", email="out@e.com", password="p")
        self.dept = Department.objects.create(name="IT", created_by=self.owner)
        UserDepartments.objects.create(user=self.mem, department=self.dept)
        UserDepartments.objects.create(user=self.owner, department=self.dept)
        self.url = reverse("department_closed_tickets", kwargs={"department_slug": self.dept.slug})

    def test_non_member_gets_403(self):
        self.client.force_login(self.out)
        self.assertEqual(self.client.get(self.url).status_code, 403)

    def test_member_sees_closed_tickets(self):
        t_open = Ticket.objects.create(title="Open", created_by=self.mem, status=Ticket.Status.OPEN)
        t_closed = Ticket.objects.create(title="Closed", created_by=self.mem, status=Ticket.Status.CLOSED)
        TicketAssigned.objects.create(ticket=t_open, department=self.dept)
        TicketAssigned.objects.create(ticket=t_closed, department=self.dept)

        self.client.force_login(self.mem)
        res = self.client.get(self.url)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.context["page"].paginator.count, 1)

    def test_empty_state(self):
        self.client.force_login(self.mem)
        res = self.client.get(self.url)
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "No closed tickets found.")
