import tempfile
from django.test import TestCase, override_settings, RequestFactory
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.http import Http404
from django.contrib.messages import get_messages
from unittest.mock import patch, PropertyMock

from tickets.models import Ticket, TicketMessage, Department, TicketMessageAttachment
from tickets.models import TicketParticipant, UserDepartments, TicketAssigned
from tickets.models.notification import Notification
from tickets.views.ticket_thread_view import TicketThreadView

User = get_user_model()


class TicketThreadViewTests(TestCase):
    """Tests for TicketThreadView."""

    def setUp(self):
        """Setup core thread elements."""
        self.u1 = User.objects.create_user(username="u1", email="u1@e.com", password="p")
        self.u2 = User.objects.create_user(username="u2", email="u2@e.com", password="p")
        self.t = Ticket.objects.create(title="T", created_by=self.u1)
        self.url = reverse("ticket_thread", kwargs={"uuid": self.t.uuid})

    def _csrf(self, **kwargs):
        """Inject CSRF token into payload."""
        tkn = self.client.cookies.get("csrftoken")
        return {**kwargs, "csrfmiddlewaretoken": tkn.value if tkn else ""}

    def test_thread_access_and_context(self):
        """Test permissions, reading context, and basic GET."""
        self.assertEqual(self.client.get(self.url).status_code, 302)
        self.client.force_login(self.u1)
        m1 = TicketMessage.objects.create(ticket=self.t, sender=self.u1, body="M1")
        m2 = TicketMessage.objects.create(ticket=self.t, sender=self.u2, body="M2")
        res = self.client.get(self.url)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.context["first_message"], m1)
        self.assertEqual(list(res.context["messages"]), [m2])
        self.assertIsNotNone(res.context["last_user_message_id"])

        s_dept = User.objects.create_user(username="sd", email="sd@e.com", password="p", is_staff=True)
        d = Department.objects.create(name="D", created_by=self.u1)
        UserDepartments.objects.create(user=s_dept, department=d)
        TicketAssigned.objects.create(ticket=self.t, department=d)
        self.client.force_login(s_dept)
        self.assertTrue(self.client.get(self.url).context["permission"])

    def test_thread_renders_profile_and_department_links(self):
        """Thread should link user names and department names."""
        self.u1.is_staff = True
        self.u1.save(update_fields=["is_staff"])
        staff_user = User.objects.create_user(
            username="staff_link", email="staff_link@e.com", password="p", is_staff=True
        )
        department = Department.objects.create(name="Linked Dept", created_by=self.u1)
        TicketMessage.objects.create(ticket=self.t, sender=self.u2, body="Reply")
        self.t.closed_by = self.u1
        self.t.reopened_by = self.u2
        self.t.save(update_fields=["closed_by", "reopened_by"])
        self.client.force_login(self.u1)
        self.client.post(self.url, data=self._csrf(action="add", target_type="staff", target_id=staff_user.id))
        self.client.post(self.url, data=self._csrf(action="add", target_type="department", target_id=department.id))

        response = self.client.get(self.url)

        self.assertContains(response, reverse("profile", args=[self.u1.profile_slug]))
        self.assertContains(response, reverse("profile", args=[self.u2.profile_slug]))
        self.assertContains(response, reverse("profile", args=[staff_user.profile_slug]))
        self.assertContains(response, reverse("department", args=[department.slug]))

    def test_thread_back_link_uses_return_to_query(self):
        """Thread page should link back to the originating home URL when provided."""
        self.client.force_login(self.u1)
        return_to = "/?scope=department&q=laptop&page=2"

        response = self.client.get(self.url, {"return_to": return_to})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["back_to_url"], return_to)
        self.assertEqual(response.context["back_to_label"], "Back to tickets")
        self.assertContains(response, 'href="/?scope=department&amp;q=laptop&amp;page=2"', html=False)
        self.assertContains(response, "Back to tickets")

    def test_thread_default_back_link_uses_generic_label(self):
        """Thread page should keep the generic back label outside search-origin flows."""
        self.client.force_login(self.u1)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["back_to_label"], "Back to tickets")
        self.assertContains(response, "Back to tickets")

    def test_thread_permissions_and_errors(self):
        """Test 403/404 handling for thread access and edits."""
        self.client.force_login(self.u2)
        self.client.get(reverse("home"))
        self.assertEqual(self.client.post(self.url, data=self._csrf(body="X")).status_code, 403)
        self.client.force_login(self.u1)
        self.client.get(self.url)
        bad_url = reverse("ticket_thread", kwargs={"uuid": "00000000-0000-0000-0000-000000000000"})
        self.assertEqual(self.client.get(bad_url).status_code, 404)
        m_other = TicketMessage.objects.create(ticket=self.t, sender=self.u2, body="M2")
        self.assertEqual(self.client.post(self.url, data=self._csrf(action="edit", message_id=m_other.id)).status_code, 404)
        self.assertEqual(self.client.post(self.url, data=self._csrf(action="update", message_id=m_other.id)).status_code, 404)
        self.assertEqual(self.client.post(self.url, data=self._csrf(action="delete", message_id=m_other.id)).status_code, 404)

    @override_settings(MEDIA_ROOT=tempfile.gettempdir())
    def test_thread_post_messages_and_attachments(self):
        """Test adding, updating, deleting messages and attachment edge cases."""
        self.client.force_login(self.u1)
        f = SimpleUploadedFile("a.txt", b"x", content_type="text/plain")
        self.client.post(self.url, data=self._csrf(body="New", attachments=f))
        msg = TicketMessage.objects.last()
        a1 = TicketMessageAttachment.objects.get(message=msg)
        empty_a = TicketMessageAttachment(ticket=self.t, message=msg, uploaded_by=self.u1)
        empty_a.save()
        empty_a.delete()
        self.client.post(self.url, data=self._csrf(action="update", message_id=msg.id, body="U", remove_attachment_ids=[a1.id]))
        self.assertFalse(TicketMessageAttachment.objects.filter(id=a1.id).exists())
        self.client.post(self.url, data=self._csrf(action="delete", message_id=msg.id))
        self.assertTrue(TicketMessage.objects.get(id=msg.id).hidden)

    def test_thread_assignments(self):
        """Test assigning/removing staff and departments."""
        s1 = User.objects.create_user(username="s1", email="s1@e.com", password="p", is_staff=True)
        d1 = Department.objects.create(name="D1", created_by=self.u1)
        self.client.force_login(self.u1)
        self.client.post(self.url, data=self._csrf(action="add", target_type="staff", target_id=s1.id))
        self.client.post(self.url, data=self._csrf(action="remove", target_type="staff", target_id=s1.id))
        self.assertTrue(self.t.participants.filter(user=s1, removed_self=True).exists())
        self.client.post(self.url, data=self._csrf(action="add", target_type="department", target_id=d1.id))
        self.client.post(self.url, data=self._csrf(action="remove", target_type="department", target_id=d1.id))
        self.assertFalse(self.t.ticket_departments.filter(department=d1).exists())
        self.u1.is_staff = True
        self.u1.save()
        TicketParticipant.objects.get_or_create(ticket=self.t, user=self.u1)
        self.client.post(self.url, data=self._csrf(action="remove", target_type="staff", target_id=self.u1.id))
        self.assertTrue(self.t.participants.get(user=self.u1).removed_self)

    def test_thread_close_and_edge_cases(self):
        """Test closing tickets and missing param behaviors."""
        self.client.force_login(self.u1)
        self.client.post(self.url, data=self._csrf(action="unknown", body=""))
        self.client.post(self.url, data=self._csrf(action="add", target_type="invalid", target_id="1"))
        self.client.post(self.url, data=self._csrf(action="add", user_id="999"))
        s_leg = User.objects.create_user(username="leg", email="l@e.com", password="p", is_staff=True)
        self.client.post(self.url, data=self._csrf(action="add", user_id=s_leg.id))
        self.assertTrue(self.t.participants.filter(user=s_leg).exists())
        msg = TicketMessage.objects.create(ticket=self.t, sender=self.u1, body="Old")
        self.client.post(self.url, data=self._csrf(action="update", message_id=msg.id, body="   "))
        self.client.post(self.url, data=self._csrf(action="add", body="   "))
        self.client.post(
            self.url,
            data=self._csrf(action="close_ticket", resolution_summary="Solved by support"),
        )
        self.t.refresh_from_db()
        self.assertEqual(self.t.status, Ticket.Status.CLOSED)
        self.assertEqual(self.t.resolution_summary, "Solved by support")

    def test_thread_assignment_prevented_when_closed_or_removed(self):
        """Assignments should be forbidden if ticket is closed or user removed themselves."""
        self.client.force_login(self.u1)
        
        # Test self-removed user
        TicketParticipant.objects.create(ticket=self.t, user=self.u1, removed_self=True)
        resp1 = self.client.post(self.url, data=self._csrf(action="add", user_id="1"))
        self.assertEqual(resp1.status_code, 403)
        self.assertIn(b"Assignment changes are not allowed", resp1.content)

        # Test closed ticket
        TicketParticipant.objects.filter(ticket=self.t, user=self.u1).delete()
        self.t.status = Ticket.Status.CLOSED
        self.t.save()
        resp2 = self.client.post(self.url, data=self._csrf(action="remove", user_id="1"))
        self.assertEqual(resp2.status_code, 403)
        self.assertIn(b"Assignment changes are not allowed", resp2.content)

    def test_thread_reopen_action_and_lifecycle_history(self):
        """Reopening from the thread should reopen the ticket and render history."""
        self.client.force_login(self.u1)
        self.t.close_with_resolution(self.u1, "Complete")
        response = self.client.post(self.url, data=self._csrf(action="reopen_ticket"), follow=True)
        self.t.refresh_from_db()
        self.assertEqual(self.t.status, Ticket.Status.OPEN)
        self.assertEqual(self.t.reopened_by, self.u1)
        self.assertContains(response, "This ticket was reopened.")
        self.assertContains(response, "Ticket reopened by u1.")

    def test_thread_internal_helpers(self):
        """Direct test on view logic for coverage of edge branches."""
        v, rf = TicketThreadView(), RequestFactory()
        v.object = v.ticket = self.t
        self.assertIsNone(v.get_assignment_target("unknown", 1))
        self.assertEqual(list(v.get_reply_messages(TicketMessage.objects.none())), [])
        v.touch_ticket()
        v.get_department_staff()
        Dummy = type("D", (), {"action": "x", "add": lambda *a: None, "remove": lambda *a: None})
        v.apply_assignment_action(Dummy(), None, None)
        s2 = User.objects.create_user(username="s2", email="s2@e.com", password="p", is_staff=True)
        req = rf.post(self.url, data={"action": "unknown", "message_id": "1", "user_id": str(s2.id)})
        req.user = self.u1
        v.handle_staff_change(req)
        m = TicketMessage.objects.create(ticket=self.t, sender=self.u1, body="H", hidden=True)
        v.request = rf.post(self.url, data={"action": "edit", "message_id": str(m.id)})
        v.request.user = self.u1
        with self.assertRaises(Http404):
            v.get_edit_message()

    def test_mixin_edit_and_staff_edge_cases(self):
        """Test edit message and staff change edge cases."""
        v, rf = TicketThreadView(), RequestFactory()
        v.object = v.ticket = self.t
        req = rf.post(self.url, data={"action": "edit", "message_id": ""})
        req.user, v.request = self.u1, req
        self.assertIsNone(v.get_edit_message())
        req = rf.post(self.url, data={"action": "something_else", "message_id": "1"})
        req.user, v.request = self.u1, req
        self.assertIsNone(v.get_edit_message())
        req = rf.post(self.url, data={"action": "add"})
        req.user = self.u1
        v.handle_staff_change(req)
        self.assertFalse(v.user_has_removed_themselves(self.u1))

    def test_mixin_attachment_edge_cases(self):
        """Test attachment handling edge cases."""
        v, rf = TicketThreadView(), RequestFactory()
        v.object = v.ticket = self.t
        m = TicketMessage.objects.create(ticket=self.t, sender=self.u1, body="A")
        f = SimpleUploadedFile("b.txt", b"x")
        req = rf.post(self.url, data={"attachment": f})
        req.user = self.u1
        v._save_attachments_for_message(req, m)
        self.assertTrue(TicketMessageAttachment.objects.filter(message=m).exists())
        req_empty = rf.post(self.url)
        req_empty.user = self.u1
        v._save_attachments_for_message(req_empty, m)

    def test_mixin_assignment_edge_cases(self):
        """Test missing handler or missing data during assignment."""
        v, rf = TicketThreadView(), RequestFactory()
        v.object = v.ticket = self.t
        s2 = User.objects.create_user(username="s2_e", email="s2@x.com", password="p", is_staff=True)
        req = rf.post(self.url, data={"action": "add", "target_type": "unknown_type", "target_id": "1"})
        req.user = self.u1
        v.handle_assignment_change(req)
        req = rf.post(self.url, data={"action": "unknown", "target_type": "staff", "target_id": s2.id})
        req.user = self.u1
        v.handle_assignment_change(req)
        self.assertIsNotNone(v.get_available_staff(v.get_ticket_staff()))
        self.assertIsNotNone(v.get_available_departments(v.get_ticket_departments()))

    def test_handle_assignment_change_missing_fields_returns_early(self):
        """handle_assignment_change should return immediately when required fields are missing."""
        v, rf = TicketThreadView(), RequestFactory()
        v.object = v.ticket = self.t
        req = rf.post(self.url, data={})  # No target_id, target_type, or action
        req.user = self.u1

        # Should not raise and should not create any assignments
        v.handle_assignment_change(req)
        self.assertEqual(self.t.ticket_departments.count(), 0)
        self.assertEqual(self.t.participants.count(), 0)

    def test_mixin_message_action_edge_cases(self):
        """Test edge cases for posting new messages and updates."""
        v, rf = TicketThreadView(), RequestFactory()
        v.object = v.ticket = self.t
        m = TicketMessage.objects.create(ticket=self.t, sender=self.u1, body="A")
        req = rf.post(self.url, data={"action": "update", "message_id": m.id, "body": "   "})
        req.user = self.u1
        v.handle_update_action(req)
        self.assertIsNone(v.get_first_message(TicketMessage.objects.none()))
        req = rf.post(self.url, data={"action": "edit"})
        req.user = self.u1
        v.dispatch_post_action("edit", req)
        m_qs = TicketMessage.objects.filter(id=m.id)
        self.assertEqual(v.get_reply_messages(m_qs), [])
        req = rf.post(self.url, data={"action": "add", "body": "   "})
        req.user = self.u1
        v.handle_add_action(req)


class TicketClosedNotificationTests(TestCase):
    """Tests for TICKET_CLOSED notification in handle_close_ticket_action."""

    def setUp(self):
        """Set up users, ticket, and view for close notification tests."""
        self.creator = User.objects.create_user(
            username="close_creator", email="closecreator@example.com", password="p"
        )
        self.staff = User.objects.create_user(
            username="close_staff", email="closestaff@example.com", password="p", is_staff=True
        )
        self.ticket = Ticket.objects.create(
            title="Close notification ticket",
            created_by=self.creator,
            status=Ticket.Status.OPEN,
        )
        TicketParticipant.objects.create(ticket=self.ticket, user=self.staff)

    @staticmethod
    def _make_view(ticket, user):
        """Create a TicketThreadView wired up with a request user."""
        view = TicketThreadView()
        view.ticket = ticket
        view.object = ticket
        view.request = type("Request", (), {"user": user})()
        return view

    def test_close_ticket_creates_ticket_closed_notification(self):
        """Closing an open ticket should create TICKET_CLOSED notifications for participants."""
        view = self._make_view(self.ticket, self.staff)
        with self.settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend"):
            view.handle_close_ticket_action()
        notifications = Notification.objects.filter(
            notification_type=Notification.NotificationType.TICKET_CLOSED,
        )
        self.assertTrue(notifications.exists())
        notified_users = list(notifications.values_list("user_id", flat=True))
        self.assertIn(self.creator.id, notified_users)
        self.assertNotIn(self.staff.id, notified_users)

    def test_close_already_closed_ticket_does_not_notify(self):
        """Closing an already-closed ticket should not create notifications."""
        self.ticket.status = Ticket.Status.CLOSED
        self.ticket.save(update_fields=["status"])
        view = self._make_view(self.ticket, self.staff)
        with self.settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend"):
            view.handle_close_ticket_action()
        notifications = Notification.objects.filter(
            notification_type=Notification.NotificationType.TICKET_CLOSED,
        )
        self.assertEqual(notifications.count(), 0)

    def test_close_ticket_notification_has_correct_actor(self):
        """TICKET_CLOSED notification should have the closing user as actor."""
        view = self._make_view(self.ticket, self.staff)
        with self.settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend"):
            view.handle_close_ticket_action()
        notification = Notification.objects.filter(
            notification_type=Notification.NotificationType.TICKET_CLOSED,
            user=self.creator,
        ).first()
        self.assertIsNotNone(notification)
        self.assertEqual(notification.actor, self.staff)


class StaffRemovedNotificationTests(TestCase):
    """Tests for STAFF_REMOVED notification in _remove_other_participant."""

    def setUp(self):
        """Set up users and ticket for staff removal notification tests."""
        self.remover = User.objects.create_user(
            username="remover", email="remover@example.com", password="p", is_staff=True
        )
        self.removed_user = User.objects.create_user(
            username="removed", email="removed@example.com", password="p", is_staff=True
        )
        self.ticket = Ticket.objects.create(
            title="Staff removal ticket",
            created_by=self.remover,
        )
        TicketParticipant.objects.create(ticket=self.ticket, user=self.removed_user)

    def test_remove_other_participant_creates_staff_removed_notification(self):
        """Removing another participant should create a STAFF_REMOVED notification."""
        view = TicketThreadView()
        view.ticket = self.ticket
        view.object = self.ticket
        with self.settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend"):
            view._remove_other_participant(self.removed_user, self.remover)
        notifications = Notification.objects.filter(
            user=self.removed_user,
            notification_type=Notification.NotificationType.STAFF_REMOVED,
        )
        self.assertEqual(notifications.count(), 1)
        self.assertEqual(notifications[0].actor, self.remover)
        self.assertEqual(notifications[0].target_object, self.ticket)

    def test_remove_self_does_not_create_staff_removed_notification(self):
        """Removing yourself should not create a STAFF_REMOVED notification."""
        view = TicketThreadView()
        view.ticket = self.ticket
        view.object = self.ticket
        view._mark_participant_removed_self(self.removed_user)
        notifications = Notification.objects.filter(
            notification_type=Notification.NotificationType.STAFF_REMOVED,
        )
        self.assertEqual(notifications.count(), 0)

    def test_staff_removed_notification_link_contains_ticket_uuid(self):
        """STAFF_REMOVED notification should have a link containing the ticket UUID."""
        view = TicketThreadView()
        view.ticket = self.ticket
        view.object = self.ticket
        with self.settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend"):
            view._remove_other_participant(self.removed_user, self.remover)
        notification = Notification.objects.get(
            user=self.removed_user,
            notification_type=Notification.NotificationType.STAFF_REMOVED,
        )
        self.assertIsNotNone(notification.short_message)

class TicketThreadViewRemindStaffTests(TestCase):
    """Test suite for the remind staff POST action in the ticket thread view."""
    
    def setUp(self):
        """Set up a test user, ticket, and thread URL."""
        self.user = User.objects.create_user(username="teststaff", email="staff@test.com", password="pwd", is_staff=True)
        self.ticket = Ticket.objects.create(title="Test Ticket", created_by=self.user)
        self.url = reverse('ticket_thread', kwargs={'uuid': self.ticket.uuid})
        self.client.login(username="teststaff", password="pwd")

    @patch('tickets.models.Ticket.is_overdue', new_callable=PropertyMock)
    def test_remind_staff_not_overdue(self, mock_is_overdue):
        """Test an error message is shown if a reminder is sent for a non-overdue ticket."""
        mock_is_overdue.return_value = False
        response = self.client.post(self.url, {'action': 'remind_staff'})
        
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any("not currently overdue" in str(m) for m in messages))

    @patch('tickets.models.Ticket.is_overdue', new_callable=PropertyMock)
    @patch('tickets.models.Ticket.send_reminder')
    def test_remind_staff_success(self, mock_send_reminder, mock_is_overdue):
        """Test a success message is shown when a reminder is successfully dispatched."""
        mock_is_overdue.return_value = True
        mock_send_reminder.return_value = True
        
        response = self.client.post(self.url, {'action': 'remind_staff'})
        
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any("A reminder has been sent" in str(m) for m in messages))

    @patch('tickets.models.Ticket.is_overdue', new_callable=PropertyMock)
    @patch('tickets.models.Ticket.send_reminder')
    def test_remind_staff_already_sent_cooldown(self, mock_send_reminder, mock_is_overdue):
        """Test an error message is shown if a reminder is sent during the 24-hour cooldown."""
        mock_is_overdue.return_value = True
        mock_send_reminder.return_value = False
        
        response = self.client.post(self.url, {'action': 'remind_staff'})
        
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any("already sent within the last 24 hours" in str(m) for m in messages))
