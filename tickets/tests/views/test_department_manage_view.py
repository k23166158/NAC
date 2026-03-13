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
    """Tests for the DepartmentManageView."""

    def _create_user(self, username, email, first_name, last_name, is_staff):
        """Helper method to create a user."""
        return User.objects.create_user(
            username=username, email=email, password="password123",
            first_name=first_name, last_name=last_name, is_staff=is_staff
        )

    def setUp(self):
        """Set up test client and users."""
        self.client = Client()
        self.url = reverse('department_manage')
        self.staff_user = self._create_user("staffuser", "staff@example.com", "Staff", "User", True)
        self.regular_user = self._create_user("regularuser", "regular@example.com", "Regular", "User", False)
        self.other_staff = self._create_user("otherstaff", "other@example.com", "Other", "Staff", True)

    def test_get_request_anonymous_user(self):
        """Test that anonymous users are redirected to login."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login/', response.url)

    def test_get_request_non_staff_user(self):
        """Test that non-staff users are denied access when accessing the view."""
        self.client.force_login(self.regular_user)
        response = self.client.get(self.url)
        # UserPassesTestMixin returns 403 Forbidden for non-staff users
        self.assertEqual(response.status_code, 403)

    def test_get_request_staff_user_no_departments(self):
        """Test that staff users see empty list when they have no departments."""
        self.client.force_login(self.staff_user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'department_manage.html')
        self.assertIn('departments', response.context)
        self.assertEqual(list(response.context['departments']), [])

    def test_get_request_staff_user_with_departments(self):
        """Test that staff users see only departments they are assigned to."""
        dept1 = Department.objects.create(name="IT Support", created_by=self.staff_user)
        dept2 = Department.objects.create(name="Finance", created_by=self.staff_user)
        dept3 = Department.objects.create(name="HR", created_by=self.other_staff)

        # Assign staff_user to dept1 and dept2
        UserDepartments.objects.create(user=self.staff_user, department=dept1)
        UserDepartments.objects.create(user=self.staff_user, department=dept2)
        # Assign other_staff to dept3
        UserDepartments.objects.create(user=self.other_staff, department=dept3)

        self.client.force_login(self.staff_user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'department_manage.html')
        self.assertIn('departments', response.context)
        
        departments = list(response.context['departments'])
        self.assertEqual(len(departments), 2)
        # Should be ordered by name
        self.assertEqual(departments[0].name, "Finance")
        self.assertEqual(departments[1].name, "IT Support")

    def test_get_request_staff_user_departments_ordered_by_name(self):
        """Test that departments are ordered by name."""
        dept1 = Department.objects.create(name="Zebra Department", created_by=self.staff_user)
        dept2 = Department.objects.create(name="Alpha Department", created_by=self.staff_user)
        dept3 = Department.objects.create(name="Beta Department", created_by=self.staff_user)

        UserDepartments.objects.create(user=self.staff_user, department=dept1)
        UserDepartments.objects.create(user=self.staff_user, department=dept2)
        UserDepartments.objects.create(user=self.staff_user, department=dept3)

        self.client.force_login(self.staff_user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        
        departments = list(response.context['departments'])
        self.assertEqual(len(departments), 3)
        self.assertEqual(departments[0].name, "Alpha Department")
        self.assertEqual(departments[1].name, "Beta Department")
        self.assertEqual(departments[2].name, "Zebra Department")

    def test_get_request_staff_user_excludes_unassigned_departments(self):
        """Test that staff users don't see departments they're not assigned to."""
        dept1 = Department.objects.create(name="Assigned Dept", created_by=self.staff_user)
        dept2 = Department.objects.create(name="Unassigned Dept", created_by=self.staff_user)

        # Only assign dept1
        UserDepartments.objects.create(user=self.staff_user, department=dept1)

        self.client.force_login(self.staff_user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        
        departments = list(response.context['departments'])
        self.assertEqual(len(departments), 1)
        self.assertEqual(departments[0].name, "Assigned Dept")

    def test_test_func_returns_true_for_staff(self):
        """Test that test_func returns True for staff users."""
        from tickets.views.department_manage_view import DepartmentManageView
        view = DepartmentManageView()
        view.request = type('Request', (), {'user': self.staff_user})()
        self.assertTrue(view.test_func())

    def test_test_func_returns_false_for_non_staff(self):
        """Test that test_func returns False for non-staff users."""
        from tickets.views.department_manage_view import DepartmentManageView
        view = DepartmentManageView()
        view.request = type('Request', (), {'user': self.regular_user})()
        self.assertFalse(view.test_func())

    def test_get_includes_pending_invitations_in_context(self):
        """Test that GET includes pending invitations for the user."""
        dept = Department.objects.create(name="Invite Dept", created_by=self.other_staff)
        inv = DepartmentInvitation.objects.create(
            sender=self.other_staff,
            recipient=self.staff_user,
            department=dept,
            status='pending',
        )
        self.client.force_login(self.staff_user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertIn('invitations', response.context)
        self.assertEqual(list(response.context['invitations']), [inv])

    def test_get_departments_have_ticket_count_annotations(self):
        """Test that departments in context have active_ticket_count and completed_ticket_count."""
        dept = Department.objects.create(name="Dept With Tickets", created_by=self.staff_user)
        UserDepartments.objects.create(user=self.staff_user, department=dept)
        ticket_open = Ticket.objects.create(
            title="Open", created_by=self.regular_user, status=Ticket.Status.OPEN
        )
        ticket_closed = Ticket.objects.create(
            title="Closed", created_by=self.regular_user, status=Ticket.Status.CLOSED
        )
        TicketAssigned.objects.create(ticket=ticket_open, department=dept)
        TicketAssigned.objects.create(ticket=ticket_closed, department=dept)
        self.client.force_login(self.staff_user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        departments = list(response.context['departments'])
        self.assertEqual(len(departments), 1)
        self.assertEqual(departments[0].active_ticket_count, 1)
        self.assertEqual(departments[0].completed_ticket_count, 1)

    def test_post_accept_invitation_success(self):
        """Test that POST action=accept accepts invite and adds user to department."""
        dept = Department.objects.create(name="Accept Dept", created_by=self.other_staff)
        inv = DepartmentInvitation.objects.create(
            sender=self.other_staff,
            recipient=self.staff_user,
            department=dept,
            status='pending',
        )
        self.client.force_login(self.staff_user)
        response = self.client.post(
            self.url,
            {'invite_id': inv.id, 'action': 'accept'},
        )
        self.assertRedirects(response, reverse('department_manage'))
        inv.refresh_from_db()
        self.assertEqual(inv.status, 'accepted')
        self.assertTrue(
            UserDepartments.objects.filter(
                user=self.staff_user,
                department=dept,
            ).exists()
        )

    def test_post_decline_invitation_success(self):
        """Test that POST action=decline declines the invite."""
        dept = Department.objects.create(name="Decline Dept", created_by=self.other_staff)
        inv = DepartmentInvitation.objects.create(
            sender=self.other_staff,
            recipient=self.staff_user,
            department=dept,
            status='pending',
        )
        self.client.force_login(self.staff_user)
        response = self.client.post(
            self.url,
            {'invite_id': inv.id, 'action': 'decline'},
        )
        self.assertRedirects(response, reverse('department_manage'))
        inv.refresh_from_db()
        self.assertEqual(inv.status, 'declined')

    def test_post_missing_invite_id_redirects_with_error(self):
        """Test that POST without invite_id redirects with error message."""
        self.client.force_login(self.staff_user)
        response = self.client.post(self.url, {'action': 'accept'})
        self.assertRedirects(response, reverse('department_manage'))

    def test_post_invalid_action_redirects_with_error(self):
        """Test that POST with invalid action redirects with error."""
        dept = Department.objects.create(name="X", created_by=self.other_staff)
        inv = DepartmentInvitation.objects.create(
            sender=self.other_staff,
            recipient=self.staff_user,
            department=dept,
            status='pending',
        )
        self.client.force_login(self.staff_user)
        response = self.client.post(
            self.url,
            {'invite_id': inv.id, 'action': 'invalid'},
        )
        self.assertRedirects(response, reverse('department_manage'))
        inv.refresh_from_db()
        self.assertEqual(inv.status, 'pending')

    def test_get_departments_filters_by_search_query(self):
        """Test that departments are filtered when search query is provided."""
        dept1 = Department.objects.create(name="Alpha Department", created_by=self.staff_user)
        dept2 = Department.objects.create(name="Beta Department", description="Searchable description", created_by=self.staff_user)

        UserDepartments.objects.create(user=self.staff_user, department=dept1)
        UserDepartments.objects.create(user=self.staff_user, department=dept2)

        self.client.force_login(self.staff_user)
        response = self.client.get(self.url, {"q": "Alpha"})
        self.assertEqual(response.status_code, 200)
        
        departments = list(response.context["departments"])
        self.assertEqual(len(departments), 1)
        self.assertEqual(departments[0].name, "Alpha Department")

        response = self.client.get(self.url, {"q": "Searchable"})
        self.assertEqual(response.status_code, 200)
        departments = list(response.context["departments"])
        self.assertEqual(len(departments), 1)
        self.assertEqual(departments[0].name, "Beta Department")

    def test_accept_invitation_creates_notification_for_sender(self):
        """Accepting an invite creates a notification for the sender."""
        dept = Department.objects.create(name="Notify Dept", created_by=self.other_staff)
        inv = DepartmentInvitation.objects.create(
            sender=self.other_staff,
            recipient=self.staff_user,
            department=dept,
            status="pending",
        )
        self.client.force_login(self.staff_user)
        self.client.post(self.url, {"invite_id": inv.id, "action": "accept"})
        notifications = Notification.objects.filter(
            user=self.other_staff,
            notification_type=Notification.NotificationType.DEPT_INVITE_ACCEPTED,
        )
        self.assertEqual(notifications.count(), 1)
        self.assertEqual(notifications[0].actor, self.staff_user)
        self.assertEqual(notifications[0].target_object, dept)

    def test_decline_invitation_creates_notification_for_sender(self):
        """Declining an invite creates a notification for the sender."""
        dept = Department.objects.create(name="Decline Notify Dept", created_by=self.other_staff)
        inv = DepartmentInvitation.objects.create(
            sender=self.other_staff,
            recipient=self.staff_user,
            department=dept,
            status="pending",
        )
        self.client.force_login(self.staff_user)
        self.client.post(self.url, {"invite_id": inv.id, "action": "decline"})
        notifications = Notification.objects.filter(
            user=self.other_staff,
            notification_type=Notification.NotificationType.DEPT_INVITE_DECLINED,
        )
        self.assertEqual(notifications.count(), 1)
        self.assertEqual(notifications[0].actor, self.staff_user)
        self.assertEqual(notifications[0].target_object, dept)

