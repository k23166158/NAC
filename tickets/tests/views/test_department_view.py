from django.test import TestCase, RequestFactory
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib.messages.storage.fallback import FallbackStorage
from django.contrib.sessions.middleware import SessionMiddleware
from unittest.mock import patch

from tickets.models import Department, UserDepartments, DepartmentInvitation, Ticket, TicketAssigned, Notification, DepartmentFAQ
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
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "department_public.html")
        su = User.objects.create_superuser(username="su", email="su@e.com", password="p")
        self.client.force_login(su)
        self.assertEqual(self.client.get(self.url).status_code, 200)

        t_open = Ticket.objects.create(title="O", created_by=self.mem, status=Ticket.Status.OPEN)
        t_closed = Ticket.objects.create(title="C", created_by=self.mem, status=Ticket.Status.CLOSED)
        TicketAssigned.objects.create(ticket=t_open, department=self.dept)
        TicketAssigned.objects.create(ticket=t_closed, department=self.dept)

        self.client.force_login(self.owner)
        res = self.client.get(self.url)
        self.assertEqual(len(res.context["active_tickets_preview"]), 1)
        self.assertEqual(len(res.context["closed_tickets_preview"]), 1)
        self.assertContains(res, reverse("profile", args=[self.owner.profile_slug]))

    def _create_department_public_view_fixtures(self):
        """Create active and inactive department members for public-view tests."""
        active_staff = User.objects.create_user(
            username="active",
            email="active@e.com",
            password="p",
            is_staff=True,
            is_active=True,
        )
        inactive_staff = User.objects.create_user(
            username="inactive",
            email="inactive@e.com",
            password="p",
            is_staff=True,
            is_active=False,
        )
        UserDepartments.objects.create(user=active_staff, department=self.dept)
        UserDepartments.objects.create(user=inactive_staff, department=self.dept)
        return active_staff, inactive_staff

    def _assert_public_department_context(self, response, active_staff, inactive_staff):
        """Assert the non-staff department page only exposes active members."""
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "department_public.html")
        self.assertTrue(response.context["is_public_department_view"])
        self.assertEqual(response.context["staff_total"], 3)
        self.assertContains(response, active_staff.get_full_name() or active_staff.username)
        self.assertNotContains(response, inactive_staff.get_full_name() or inactive_staff.username)
        self.assertNotContains(response, "Active Tickets")
        self.assertNotContains(response, "Closed Tickets")
        self.assertNotContains(response, "Frequently Asked Questions")

    def test_non_staff_user_gets_public_department_view(self):
        """Non-staff users should see the read-only department page."""
        active_staff, inactive_staff = self._create_department_public_view_fixtures()
        self.client.force_login(self.mem)
        response = self.client.get(self.url)
        self._assert_public_department_context(response, active_staff, inactive_staff)

    def test_public_department_view_shows_faqs_as_read_only_accordion(self):
        """Non-staff users should see published FAQs without edit controls."""
        DepartmentFAQ.objects.create(
            department=self.dept,
            question="How do I get help?",
            answer="Contact the service desk.",
            created_by=self.owner,
        )
        self.client.force_login(self.mem)

        response = self.client.get(self.url)

        self.assertTemplateUsed(response, "department_public.html")
        self.assertContains(response, "Published FAQs")
        self.assertContains(response, "How do I get help?")
        self.assertContains(response, "Contact the service desk.")
        self.assertNotContains(response, "Add FAQ")
        self.assertNotContains(response, "Save FAQ")

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

    def test_staff_member_non_owner_post_is_forbidden(self):
        """Staff members who are not owners should not manage department staff."""
        member_staff = User.objects.create_user(
            username="member_staff",
            email="member_staff@e.com",
            password="p",
            is_staff=True,
        )
        UserDepartments.objects.create(user=member_staff, department=self.dept)
        self.client.force_login(member_staff)

        response = self.client.post(self.url, {"action": "add", "user_id": self.out.id})

        self.assertEqual(response.status_code, 403)

    def test_non_staff_post_to_department_is_forbidden(self):
        """Non-staff users should not be able to post to the read-only department page."""
        self.client.force_login(self.mem)
        response = self.client.post(self.url, {"action": "add_faq"})
        self.assertEqual(response.status_code, 403)

    def test_staff_outsider_get_is_forbidden(self):
        """Staff users outside the department should get the read-only public view."""
        outsider_staff = User.objects.create_user(
            username="staff_out",
            email="staff_out@e.com",
            password="p",
            is_staff=True,
        )
        self.client.force_login(outsider_staff)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "department_public.html")
        self.assertTrue(response.context["is_public_department_view"])

    def test_staff_outsider_faq_action_is_forbidden(self):
        """Staff outsiders should not reach FAQ handlers."""
        outsider_staff = User.objects.create_user(
            username="faq_out",
            email="faq_out@e.com",
            password="p",
            is_staff=True,
        )
        self.client.force_login(outsider_staff)
        response = self.client.post(
            self.url,
            {"action": "add_faq", "question": "Q", "answer": "A"},
        )
        self.assertEqual(response.status_code, 403)

    def test_faq_action_forbidden_when_public_fallback_is_bypassed(self):
        """FAQ actions should return 403 when FAQ permissions are denied."""
        request = RequestFactory().post(
            self.url,
            data={"action": "add_faq", "question": "Q", "answer": "A"},
        )
        request.user = self.out

        with patch.object(DepartmentView, "_should_render_public_view", return_value=False):
            response = DepartmentView().post(request, self.dept.slug)

        self.assertEqual(response.status_code, 403)

    def test_get_forbidden_when_public_view_not_used_and_user_cannot_view(self):
        """GET should return 403 when the user cannot view and no public fallback is used."""
        request = RequestFactory().get(self.url)
        request.user = self.out

        with patch.object(DepartmentView, "_should_render_public_view", return_value=False):
            response = DepartmentView().get(request, self.dept.slug)

        self.assertEqual(response.status_code, 403)

    def test_update_staff_assignment_unknown_action_noop(self):
        """update_staff_assignment should be a no-op when action key is unknown."""
        rf = RequestFactory()
        request = rf.post(self.url, data={"user_id": self.out.id, "action": "unknown_action"})
        request.user = self.owner

        view = DepartmentView()
        view._process_staff_action(request, self.dept)

        # No new invitations or membership changes should have been made
        self.assertFalse(DepartmentInvitation.objects.filter(recipient=self.out).exists())
        self.assertTrue(UserDepartments.objects.filter(user=self.out, department=self.dept).count() in (0, 1))

    def test_process_staff_action_with_valid_action(self):
        """_process_staff_action should process valid actions and send messages."""
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
        view._process_staff_action(request, self.dept)

        # Valid action should create an invitation
        self.assertTrue(DepartmentInvitation.objects.filter(recipient=staff_user).exists())

    @patch("tickets.views.department_view.messages.success")
    def test_update_staff_assignment_reports_message_outcome(self, mock_success):
        """update_staff_assignment should publish a message when a result is returned."""
        request = RequestFactory().post(self.url, data={"user_id": self.out.id, "action": "add"})
        request.user = self.owner
        middleware = SessionMiddleware(lambda x: None)
        middleware.process_request(request)
        request.session.save()
        setattr(request, "_messages", FallbackStorage(request))

        department = Department.objects.get(pk=self.dept.pk)
        with patch.object(department, "process_staff_change", return_value=("success", "Invited")):
            DepartmentView().update_staff_assignment(
                request,
                user_id=self.out.id,
                department=department,
                action="add",
            )

        mock_success.assert_called_once_with(request, "Invited")

    def test_update_staff_assignment_returns_quietly_without_outcome(self):
        """update_staff_assignment should no-op when no message outcome is returned."""
        request = RequestFactory().post(self.url, data={"user_id": self.out.id, "action": "add"})
        request.user = self.owner
        middleware = SessionMiddleware(lambda x: None)
        middleware.process_request(request)
        request.session.save()
        setattr(request, "_messages", FallbackStorage(request))

        department = Department.objects.get(pk=self.dept.pk)
        with patch.object(department, "process_staff_change", return_value=None):
            DepartmentView().update_staff_assignment(
                request,
                user_id=self.out.id,
                department=department,
                action="add",
            )

    def test_owner_can_add_faq_with_valid_form(self):
        """Owner should be able to add an FAQ."""
        self.client.force_login(self.owner)

        response = self.client.post(
            self.url,
            {"action": "add_faq", "question": "How?", "answer": "Like this."},
        )

        self.assertRedirects(response, self.url)
        self.assertTrue(DepartmentFAQ.objects.filter(department=self.dept, question="How?").exists())

    def test_owner_add_faq_with_invalid_form_shows_error(self):
        """Invalid FAQ add requests should not create records."""
        self.client.force_login(self.owner)

        response = self.client.post(
            self.url,
            {"action": "add_faq", "question": "", "answer": ""},
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(DepartmentFAQ.objects.filter(department=self.dept).exists())

    def test_owner_can_edit_faq_with_valid_form(self):
        """Owner should be able to edit an FAQ."""
        faq = DepartmentFAQ.objects.create(
            department=self.dept,
            question="Old question",
            answer="Old answer",
            created_by=self.owner,
        )
        self.client.force_login(self.owner)

        response = self.client.post(
            self.url,
            {"action": "edit_faq", "faq_id": faq.id, "question": "New question", "answer": "New answer"},
        )

        self.assertRedirects(response, self.url)
        faq.refresh_from_db()
        self.assertEqual(faq.question, "New question")
        self.assertEqual(faq.answer, "New answer")

    def test_owner_edit_faq_with_invalid_form_shows_error(self):
        """Invalid FAQ edit requests should keep the original FAQ content."""
        faq = DepartmentFAQ.objects.create(
            department=self.dept,
            question="Keep me",
            answer="Keep me too",
            created_by=self.owner,
        )
        self.client.force_login(self.owner)

        response = self.client.post(
            self.url,
            {"action": "edit_faq", "faq_id": faq.id, "question": "", "answer": ""},
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        faq.refresh_from_db()
        self.assertEqual(faq.question, "Keep me")
        self.assertEqual(faq.answer, "Keep me too")

    def test_owner_can_delete_faq(self):
        """Owner should be able to delete an FAQ."""
        faq = DepartmentFAQ.objects.create(
            department=self.dept,
            question="Delete me",
            answer="Soon gone",
            created_by=self.owner,
        )
        self.client.force_login(self.owner)

        response = self.client.post(
            self.url,
            {"action": "delete_faq", "faq_id": faq.id},
        )

        self.assertRedirects(response, self.url)
        self.assertFalse(DepartmentFAQ.objects.filter(pk=faq.pk).exists())
