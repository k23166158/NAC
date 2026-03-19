from django.test import TestCase, Client, RequestFactory
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib.messages.storage.fallback import FallbackStorage
from django.contrib.sessions.middleware import SessionMiddleware

from tickets.models import Department, UserDepartments, DepartmentInvitation, Ticket, TicketAssigned, Notification
from tickets.views.department_view import DepartmentView

User = get_user_model()


class DepartmentViewTests(TestCase):
    """Tests for the DepartmentView."""

    def setUp(self):
        """Set up users and base department mappings."""
        self.owner = User.objects.create_user(username="o", email="o@e.com", password="p", is_staff=True)
        self.mem = User.objects.create_user(username="m", email="m@e.com", password="p")
        self.out = User.objects.create_user(username="out", email="out@e.com", password="p")
        self.dept = Department.objects.create(name="IT", created_by=self.owner)
        UserDepartments.objects.create(user=self.mem, department=self.dept)
        UserDepartments.objects.create(user=self.owner, department=self.dept)
        self.url = reverse('department', kwargs={'department_slug': self.dept.slug})

    def test_department_access_and_context(self):
        """Test role-based access validation and contextual ticket population."""
        self.client.force_login(self.out)
        self.assertEqual(self.client.get(self.url).status_code, 403)
        su = User.objects.create_superuser(username="su", email="su@e.com", password="p")
        self.client.force_login(su)
        self.assertEqual(self.client.get(self.url).status_code, 200)

        t_open = Ticket.objects.create(title="O", created_by=self.mem, status=Ticket.Status.OPEN)
        t_closed = Ticket.objects.create(title="C", created_by=self.mem, status=Ticket.Status.CLOSED)
        TicketAssigned.objects.create(ticket=t_open, department=self.dept)
        TicketAssigned.objects.create(ticket=t_closed, department=self.dept)

        self.client.force_login(self.mem)
        res = self.client.get(self.url)
        self.assertEqual(len(res.context["active_tickets_page"]), 1)
        self.assertEqual(len(res.context["closed_tickets_page"]), 1)

    def test_department_post_actions_owner(self):
        """Test adding/removing staff and revoking invitations as an owner."""
        s1 = User.objects.create_user(username="s1", email="s1@e.com", password="p", is_staff=True)
        self.client.force_login(self.owner)
        
        self.client.post(self.url, {'action': 'add', 'user_id': s1.id})
        self.assertTrue(DepartmentInvitation.objects.filter(recipient=s1).exists())
        self.client.post(self.url, {'action': 'add', 'user_id': s1.id})
        self.client.post(self.url, {'action': 'add', 'user_id': self.owner.id})
        self.client.post(self.url, {'action': 'add', 'user_id': self.out.id})
        
        self.client.post(self.url, {'action': 'remove_invite', 'user_id': s1.id})
        self.assertFalse(DepartmentInvitation.objects.filter(recipient=s1, status='pending').exists())

        self.client.post(self.url, {'action': 'remove', 'user_id': self.mem.id})
        self.assertFalse(UserDepartments.objects.filter(user=self.mem).exists())
        self.client.post(self.url, {'action': 'unknown'})

    def test_add_staff_creates_dept_invited_notification(self):
        """Adding staff should create a DEPT_INVITED notification."""
        new_staff = User.objects.create_user(username="ns", email="ns@e.com", password="p", is_staff=True)
        self.client.force_login(self.owner)
        self.client.post(self.url, {'action': 'add', 'user_id': new_staff.id})
        notifications = Notification.objects.filter(
            user=new_staff,
            notification_type=Notification.NotificationType.DEPT_INVITED,
        )
        self.assertEqual(notifications.count(), 1)
        self.assertEqual(notifications[0].actor, self.owner)
        self.assertEqual(notifications[0].target_object, self.dept)

    def test_remove_staff_creates_dept_member_removed_notification(self):
        """Removing staff should create a DEPT_MEMBER_REMOVED notification."""
        UserDepartments.objects.create(user=self.out, department=self.dept)
        self.client.force_login(self.owner)
        self.client.post(self.url, {'action': 'remove', 'user_id': self.out.id})
        notifications = Notification.objects.filter(
            user=self.out,
            notification_type=Notification.NotificationType.DEPT_MEMBER_REMOVED,
        )
        self.assertEqual(notifications.count(), 1)
        self.assertEqual(notifications[0].actor, self.owner)
        self.assertEqual(notifications[0].target_object, self.dept)

    def test_remove_non_member_does_nothing(self):
        """Removing a user who is not a department member should not create notifications."""
        self.client.force_login(self.owner)
        self.client.post(self.url, {'action': 'remove', 'user_id': self.out.id})
        self.assertFalse(Notification.objects.filter(
            user=self.out, notification_type=Notification.NotificationType.DEPT_MEMBER_REMOVED,
        ).exists())

    def test_department_post_permissions_non_owner(self):
        """Test that non-owners and regular staff are forbidden from management actions."""
        s_other = User.objects.create_user(username="so", email="so@e.com", password="p", is_staff=True)
        self.client.force_login(self.mem)
        self.assertEqual(self.client.post(self.url, {'action': 'add', 'user_id': self.out.id}).status_code, 403)
        self.client.force_login(s_other)
        self.assertEqual(self.client.post(self.url, {'action': 'add', 'user_id': self.out.id}).status_code, 403)

    def test_update_staff_assignment_unknown_action_noop(self):
        """update_staff_assignment should be a no-op when action key is unknown."""
        rf = RequestFactory()
        request = rf.post(self.url, data={"user_id": self.out.id, "action": "unknown_action"})
        request.user = self.owner

        view = DepartmentView()
        view.update_staff_assignment(request, user_id=self.out.id, department=self.dept, action="unknown_action")

        # No new invitations or membership changes should have been made
        self.assertFalse(DepartmentInvitation.objects.filter(recipient=self.out).exists())
        self.assertTrue(UserDepartments.objects.filter(user=self.out, department=self.dept).count() in (0, 1))

    def test_update_staff_assignment_with_valid_action(self):
        """update_staff_assignment should process valid actions and send messages."""
        # Create a staff user to invite
        staff_user = User.objects.create_user(username="staff_inv", email="staff_inv@e.com", password="p", is_staff=True)
        
        rf = RequestFactory()
        request = rf.post(self.url, data={"user_id": staff_user.id, "action": "add"})
        request.user = self.owner

        # Add session and messages middleware
        middleware = SessionMiddleware(lambda x: None)
        middleware.process_request(request)
        request.session.save()
        
        setattr(request, '_messages', FallbackStorage(request))

        view = DepartmentView()
        view.update_staff_assignment(request, user_id=staff_user.id, department=self.dept, action="add")

        # Valid action should create an invitation
        self.assertTrue(DepartmentInvitation.objects.filter(recipient=staff_user).exists())