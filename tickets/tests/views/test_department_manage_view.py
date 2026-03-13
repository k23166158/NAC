from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from tickets.models import Department, DepartmentInvitation, UserDepartments, Ticket, TicketAssigned

User = get_user_model()

class DepartmentManageViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.url = reverse('department_manage')
        self.staff = User.objects.create_user(username="staff", email="s@example.com", password="123", is_staff=True)
        self.reg = User.objects.create_user(username="reg", email="r@example.com", password="123", is_staff=False)
        self.other = User.objects.create_user(username="other", email="o@example.com", password="123", is_staff=True)

    def test_access_permissions(self):
        resp = self.client.get(self.url)
        self.assertIn('/login/', resp.url)
        
        self.client.force_login(self.reg)
        self.assertEqual(self.client.get(self.url).status_code, 403)

    def test_get_comprehensive_context(self):
        dept_z = Department.objects.create(name="Zebra", created_by=self.staff)
        dept_a = Department.objects.create(name="Alpha", description="Match this", created_by=self.staff)
        dept_u = Department.objects.create(name="Unassigned", created_by=self.staff)
        
        UserDepartments.objects.create(user=self.staff, department=dept_z)
        UserDepartments.objects.create(user=self.staff, department=dept_a)
        
        t1 = Ticket.objects.create(title="T1", created_by=self.reg, status=Ticket.Status.OPEN)
        t2 = Ticket.objects.create(title="T2", created_by=self.reg, status=Ticket.Status.CLOSED)
        TicketAssigned.objects.create(ticket=t1, department=dept_a)
        TicketAssigned.objects.create(ticket=t2, department=dept_a)
        
        inv = DepartmentInvitation.objects.create(
            sender=self.other, recipient=self.staff, department=dept_u, status='pending'
        )

        self.client.force_login(self.staff)
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)
        
        depts = list(resp.context['departments'])
        self.assertEqual(len(depts), 2)
        self.assertEqual(depts[0].name, "Alpha")
        self.assertEqual(depts[1].name, "Zebra")
        self.assertEqual(depts[0].active_ticket_count, 1)
        self.assertEqual(depts[0].completed_ticket_count, 1)
        self.assertEqual(list(resp.context['invitations']), [inv])
        
        resp_search = self.client.get(self.url, {"q": "Match"})
        self.assertEqual(len(list(resp_search.context['departments'])), 1)
        self.assertEqual(resp_search.context['departments'][0].name, "Alpha")

    def test_post_invitations_handling(self):
        self.client.force_login(self.staff)
        dept_a = Department.objects.create(name="A", created_by=self.other)
        dept_d = Department.objects.create(name="D", created_by=self.other)
        
        inv_a = DepartmentInvitation.objects.create(
            sender=self.other, recipient=self.staff, department=dept_a, status='pending'
        )
        inv_d = DepartmentInvitation.objects.create(
            sender=self.other, recipient=self.staff, department=dept_d, status='pending'
        )
        
        self.assertRedirects(self.client.post(self.url, {'action': 'accept'}), self.url)
        self.assertRedirects(self.client.post(self.url, {'invite_id': inv_a.id, 'action': 'invalid'}), self.url)
        
        self.client.post(self.url, {'invite_id': inv_a.id, 'action': 'accept'})
        inv_a.refresh_from_db()
        self.assertEqual(inv_a.status, 'accepted')
        self.assertTrue(UserDepartments.objects.filter(user=self.staff, department=dept_a).exists())
        
        self.client.post(self.url, {'invite_id': inv_d.id, 'action': 'decline'})
        inv_d.refresh_from_db()
        self.assertEqual(inv_d.status, 'declined')