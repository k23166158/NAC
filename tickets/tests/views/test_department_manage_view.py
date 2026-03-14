from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from tickets.models import (
    Department,
    DepartmentInvitation,
    UserDepartments,
    Ticket,
    TicketAssigned,
    Notification,
)

User = get_user_model()

class DepartmentManageViewTests(TestCase):
    """Tests for department manage view."""

    def setUp(self):
        """Set up test client and user accounts."""
        self.client = Client()
        self.url = reverse('department_manage')
        self.staff = User.objects.create_user(username="staff", email="s@example.com", password="123", is_staff=True)
        self.reg = User.objects.create_user(username="reg", email="r@example.com", password="123", is_staff=False)
        self.other = User.objects.create_user(username="other", email="o@example.com", password="123", is_staff=True)

    def test_access_permissions(self):
        """Test access restrictions for unauthenticated and non-staff users."""
        resp = self.client.get(self.url)
        self.assertIn('/login/', resp.url)
        
        self.client.force_login(self.reg)
        self.assertEqual(self.client.get(self.url).status_code, 403)

    def test_get_comprehensive_context(self):
        """Test department listing, ticket counts, and pending invitations."""
        dept = Department.objects.create(name="Alpha", created_by=self.staff)
        UserDepartments.objects.create(user=self.staff, department=dept)
        
        t1 = Ticket.objects.create(title="T1", created_by=self.reg, status=Ticket.Status.OPEN)
        t2 = Ticket.objects.create(title="T2", created_by=self.reg, status=Ticket.Status.CLOSED)
        TicketAssigned.objects.create(ticket=t1, department=dept)
        TicketAssigned.objects.create(ticket=t2, department=dept)
        
        inv = DepartmentInvitation.objects.create(
            sender=self.other, recipient=self.staff, department=dept, status='pending'
        )

        self.client.force_login(self.staff)
        resp = self.client.get(self.url)
        
        depts = list(resp.context['departments'])
        self.assertEqual(depts[0].active_ticket_count, 1)
        self.assertEqual(depts[0].completed_ticket_count, 1)
        self.assertEqual(list(resp.context['invitations']), [inv])

    def test_get_search_filtering(self):
        """Test that departments can be filtered by a search query."""
        dept_z = Department.objects.create(name="Zebra", created_by=self.staff)
        dept_a = Department.objects.create(name="Alpha", description="Match", created_by=self.staff)
        UserDepartments.objects.create(user=self.staff, department=dept_z)
        UserDepartments.objects.create(user=self.staff, department=dept_a)
        
        self.client.force_login(self.staff)
        resp_search = self.client.get(self.url, {"q": "Match"})
        
        depts = list(resp_search.context['departments'])
        self.assertEqual(len(depts), 1)
        self.assertEqual(depts[0].name, "Alpha")

    def test_post_invitations_handling(self):
        """Test accepting, declining, and invalid invitation actions."""
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

        self.client.post(self.url, {'invite_id': inv_d.id, 'action': 'decline'})
        inv_d.refresh_from_db()
        self.assertEqual(inv_d.status, 'declined')

    def test_accept_invitation_creates_notification_for_sender(self):
        """Accepting an invite creates a notification for the sender."""
        dept = Department.objects.create(name="Notify Dept", created_by=self.other)
        inv = DepartmentInvitation.objects.create(
            sender=self.other,
            recipient=self.staff,
            department=dept,
            status="pending",
        )
        self.client.force_login(self.staff)
        self.client.post(self.url, {"invite_id": inv.id, "action": "accept"})
        notifications = Notification.objects.filter(
            user=self.other,
            notification_type=Notification.NotificationType.DEPT_INVITE_ACCEPTED,
        )
        self.assertEqual(notifications.count(), 1)
        self.assertEqual(notifications[0].actor, self.staff)
        self.assertEqual(notifications[0].target_object, dept)

    def test_decline_invitation_creates_notification_for_sender(self):
        """Declining an invite creates a notification for the sender."""
        dept = Department.objects.create(name="Decline Notify Dept", created_by=self.other)
        inv = DepartmentInvitation.objects.create(
            sender=self.other,
            recipient=self.staff,
            department=dept,
            status="pending",
        )
        self.client.force_login(self.staff)
        self.client.post(self.url, {"invite_id": inv.id, "action": "decline"})
        notifications = Notification.objects.filter(
            user=self.other,
            notification_type=Notification.NotificationType.DEPT_INVITE_DECLINED,
        )
        self.assertEqual(notifications.count(), 1)
        self.assertEqual(notifications[0].actor, self.staff)
        self.assertEqual(notifications[0].target_object, dept)
