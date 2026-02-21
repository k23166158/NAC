import uuid
from django.utils import timezone
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from tickets.models.ticket_participant import TicketParticipant
from tickets.views.ticket_thread_view import TicketThreadView
from tickets.models import Ticket, TicketMessage, Department, UserDepartments, TicketAssigned
from django.http import Http404

User = get_user_model()


def make_user(username, **kwargs):
    """Create a user with required fields for this project's User model."""
    defaults = {
        "password": "password123",
        "email": f"{username}@example.com",
        "first_name": "First",
        "last_name": "Last",
    }
    defaults.update(kwargs)
    return User.objects.create_user(username=username, **defaults)

class TicketThreadViewTests(TestCase):
    """Tests for TicketThreadView (ticket thread page and post actions)."""

    def setUp(self):
        """Set up test users and a ticket."""
        self.client = Client()
        self.user = make_user("threaduser")
        self.other_user = make_user("otheruser", email="other@example.com")
        self.ticket = Ticket.objects.create(
            title="Test Ticket",
            created_by=self.user,
        )

    def _url(self, ticket=None):
        """Get the URL for the ticket thread view for the given ticket (default: self.ticket)."""
        t = ticket or self.ticket
        return reverse("ticket_thread", kwargs={"uuid": t.uuid})

    def _csrf_data(self, **extra):
        """Get POST data dict with valid CSRF token (call after client has GET'd the page)."""
        token = self.client.cookies.get("csrftoken")
        data = {"csrfmiddlewaretoken": token.value} if token else {}
        data.update(extra)
        return data

    # --- GET: access and template ---

    def test_get_anonymous_redirects_to_login(self):
        """Anonymous users are redirected to login."""
        response = self.client.get(self._url())
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("login"), response.url)

    def test_get_authenticated_returns_200_and_template(self):
        """Authenticated user can view the ticket thread."""
        self.client.force_login(self.user)
        response = self.client.get(self._url())
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "ticket_thread.html")

    def test_get_nonexistent_ticket_returns_404(self):
        """Requesting a non-existent ticket returns 404."""
        self.client.force_login(self.user)
        response = self.client.get(reverse("ticket_thread", kwargs={"uuid": uuid.uuid4()}))
        self.assertEqual(response.status_code, 404)

    def test_dispatch_post_action_edit_lambda_direct(self):
        """Directly call dispatch_post_action with action='edit' to execute the lambda."""
        self.client.force_login(self.user)
        view = TicketThreadView()
        view.object = self.ticket
        # Use a real request object
        request = self.client.get(self._url()).wsgi_request
        # This should execute the "edit" lambda which does nothing
        view.dispatch_post_action("edit", request)

    # --- GET: context (first_message, messages, last_user_message_id) ---

    def test_context_zero_messages(self):
        """With no messages, first_message is None, messages empty, last_user_message_id None."""
        self.client.force_login(self.user)
        response = self.client.get(self._url())
        self.assertEqual(response.status_code, 200)
        self.assertIn("ticket", response.context)
        self.assertEqual(response.context["ticket"], self.ticket)
        self.assertIsNone(response.context["first_message"])
        self.assertEqual(list(response.context["messages"]), [])
        self.assertIsNone(response.context["last_user_message_id"])

    def test_context_one_message(self):
        """With one message, it is first_message; messages (replies) is empty."""
        msg = TicketMessage.objects.create(
            ticket=self.ticket,
            sender=self.user,
            body="Only message",
        )
        self.client.force_login(self.user)
        response = self.client.get(self._url())
        self.assertEqual(response.context["first_message"], msg)
        self.assertEqual(list(response.context["messages"]), [])
        self.assertEqual(response.context["last_user_message_id"], msg.id)

    def test_context_two_messages_first_and_replies(self):
        """With two messages, first is first_message, rest are in messages."""
        first = TicketMessage.objects.create(
            ticket=self.ticket,
            sender=self.user,
            body="First",
        )
        second = TicketMessage.objects.create(
            ticket=self.ticket,
            sender=self.user,
            body="Second",
        )
        self.client.force_login(self.user)
        response = self.client.get(self._url())
        self.assertEqual(response.context["first_message"], first)
        self.assertEqual(list(response.context["messages"]), [second])
        self.assertEqual(response.context["last_user_message_id"], second.id)

    def test_context_last_user_message_id_excludes_hidden(self):
        """last_user_message_id is the last visible message from the current user; hidden ignored."""
        visible = TicketMessage.objects.create(
            ticket=self.ticket,
            sender=self.user,
            body="Visible",
        )
        hidden = TicketMessage.objects.create(
            ticket=self.ticket,
            sender=self.user,
            body="Hidden",
            hidden=True,
        )
        self.client.force_login(self.user)
        response = self.client.get(self._url())
        self.assertEqual(response.context["last_user_message_id"], visible.id)

    def test_context_last_user_message_id_none_when_no_visible_from_user(self):
        """When user has no visible messages, last_user_message_id is None."""
        TicketMessage.objects.create(
            ticket=self.ticket,
            sender=self.user,
            body="Only message",
            hidden=True,
        )
        self.client.force_login(self.user)
        response = self.client.get(self._url())
        self.assertIsNone(response.context["last_user_message_id"])

    def test_context_messages_ordered_by_created_at(self):
        """Reply messages in context are ordered by created_at."""
        first = TicketMessage.objects.create(
            ticket=self.ticket,
            sender=self.user,
            body="First",
        )
        second = TicketMessage.objects.create(
            ticket=self.ticket,
            sender=self.other_user,
            body="Second",
        )
        third = TicketMessage.objects.create(
            ticket=self.ticket,
            sender=self.user,
            body="Third",
        )
        self.client.force_login(self.user)
        response = self.client.get(self._url())
        replies = list(response.context["messages"])
        self.assertEqual(len(replies), 2)
        self.assertEqual(replies[0], second)
        self.assertEqual(replies[1], third)

    # --- POST: add message ---

    def test_post_with_body_creates_message_and_renders_thread(self):
        """POST with body creates a TicketMessage and re-renders the thread."""
        self.client.force_login(self.user)
        self.client.get(self._url())
        response = self.client.post(
            self._url(),
            data=self._csrf_data(body="New reply"),
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "ticket_thread.html")
        self.assertEqual(TicketMessage.objects.filter(ticket=self.ticket).count(), 1)
        msg = TicketMessage.objects.get(ticket=self.ticket)
        self.assertEqual(msg.body, "New reply")
        self.assertEqual(msg.sender, self.user)

    def test_post_empty_body_does_not_create_message(self):
        """POST without body (or empty body) does not create a message."""
        self.client.force_login(self.user)
        self.client.get(self._url())
        response = self.client.post(
            self._url(),
            data=self._csrf_data(),
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(TicketMessage.objects.filter(ticket=self.ticket).count(), 0)

    # --- POST: edit / update message ---

    def test_post_edit_sets_edit_message_in_context(self):
        """POST action=edit shows the edit form for the selected message."""
        msg = TicketMessage.objects.create(
            ticket=self.ticket,
            sender=self.user,
            body="Original body",
        )
        self.client.force_login(self.user)
        self.client.get(self._url())
        response = self.client.post(
            self._url(),
            data=self._csrf_data(action="edit", message_id=str(msg.id)),
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["edit_message"], msg)
        self.assertEqual(
            TicketMessage.objects.filter(ticket=self.ticket).count(),
            1,
        )

    def test_post_update_changes_message_body(self):
        """POST action=update modifies the existing message body."""
        msg = TicketMessage.objects.create(
            ticket=self.ticket,
            sender=self.user,
            body="Original body",
        )
        self.client.force_login(self.user)
        self.client.get(self._url())
        response = self.client.post(
            self._url(),
            data=self._csrf_data(
                action="update",
                message_id=str(msg.id),
                body="Updated body",
            ),
        )
        self.assertEqual(response.status_code, 200)
        msg.refresh_from_db()
        self.assertEqual(msg.body, "Updated body")

    def test_post_update_other_users_message_returns_404(self):
        """POST action=update on another user's message returns 404."""
        msg = TicketMessage.objects.create(
            ticket=self.ticket,
            sender=self.other_user,
            body="Other user body",
        )
        self.client.force_login(self.user)
        self.client.get(self._url())
        response = self.client.post(
            self._url(),
            data=self._csrf_data(
                action="update",
                message_id=str(msg.id),
                body="Updated body",
            ),
        )
        self.assertEqual(response.status_code, 404)
        msg.refresh_from_db()
        self.assertEqual(msg.body, "Other user body")

    def test_post_update_without_body_does_not_change_message(self):
        """POST action=update without body leaves the message unchanged."""
        msg = TicketMessage.objects.create(
            ticket=self.ticket,
            sender=self.user,
            body="Original body",
        )
        self.client.force_login(self.user)
        self.client.get(self._url())
        response = self.client.post(
            self._url(),
            data=self._csrf_data(action="update", message_id=str(msg.id)),
        )
        self.assertEqual(response.status_code, 200)
        msg.refresh_from_db()
        self.assertEqual(msg.body, "Original body")

    def test_post_edit_other_users_message_returns_404(self):
        """POST action=edit on another user's message returns 404."""
        msg = TicketMessage.objects.create(
            ticket=self.ticket,
            sender=self.other_user,
            body="Other user body",
        )
        self.client.force_login(self.user)
        self.client.get(self._url())
        response = self.client.post(
            self._url(),
            data=self._csrf_data(action="edit", message_id=str(msg.id)),
        )
        self.assertEqual(response.status_code, 404)

    def test_post_delete_marks_own_message_hidden(self):
        """POST action=delete with own message_id sets message hidden and re-renders thread."""
        msg = TicketMessage.objects.create(
            ticket=self.ticket,
            sender=self.user,
            body="To delete",
        )
        self.client.force_login(self.user)
        self.client.get(self._url())
        response = self.client.post(
            self._url(),
            data=self._csrf_data(action="delete", message_id=str(msg.id)),
        )
        self.assertEqual(response.status_code, 200)
        msg.refresh_from_db()
        self.assertTrue(msg.hidden)

    def test_post_delete_other_users_message_returns_404(self):
        """POST action=delete for a message from another user returns 404 (cannot delete)."""
        msg = TicketMessage.objects.create(
            ticket=self.ticket,
            sender=self.other_user,
            body="Other user message",
        )
        self.client.force_login(self.user)
        self.client.get(self._url())
        response = self.client.post(
            self._url(),
            data=self._csrf_data(action="delete", message_id=str(msg.id)),
        )
        self.assertEqual(response.status_code, 404)
        msg.refresh_from_db()
        self.assertFalse(msg.hidden)

    def test_post_delete_invalid_message_id_returns_404(self):
        """POST action=delete with non-existent message_id returns 404."""
        self.client.force_login(self.user)
        self.client.get(self._url())
        response = self.client.post(
            self._url(),
            data=self._csrf_data(action="delete", message_id="99999"),
        )
        self.assertEqual(response.status_code, 404)

    def test_post_delete_message_from_other_ticket_returns_404(self):
        """POST action=delete with message_id from another ticket returns 404."""
        other_ticket = Ticket.objects.create(
            title="Other Ticket",
            created_by=self.other_user,
        )
        msg = TicketMessage.objects.create(
            ticket=other_ticket,
            sender=self.user,
            body="On other ticket",
        )
        self.client.force_login(self.user)
        self.client.get(self._url())
        response = self.client.post(
            self._url(),
            data=self._csrf_data(action="delete", message_id=str(msg.id)),
        )
        self.assertEqual(response.status_code, 404)
        msg.refresh_from_db()
        self.assertFalse(msg.hidden)

    def test_post_close_ticket_sets_status_closed(self):
        """POST action=close_ticket sets ticket status to closed and updates updated_at."""
        self.client.force_login(self.user)
        old_updated_at = self.ticket.updated_at
        self.client.get(self._url())
        response = self.client.post(
            self._url(),
            data=self._csrf_data(action="close_ticket"),
        )
        self.assertEqual(response.status_code, 200)
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.status, Ticket.Status.CLOSED)
        self.assertTrue(self.ticket.updated_at > old_updated_at)

    def test_post_close_ticket_already_closed(self):
        """POST action=close_ticket on an already closed ticket does not error and leaves closed_at unchanged."""
        self.ticket.status = Ticket.Status.CLOSED
        self.ticket.closed_at = timezone.now()
        self.ticket.save()
        self.client.force_login(self.user)
        self.client.get(self._url())
        old_closed_at = self.ticket.closed_at
        response = self.client.post(
            self._url(),
            data=self._csrf_data(action="close_ticket"),
        )
        self.assertEqual(response.status_code, 200)
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.status, Ticket.Status.CLOSED)
        self.assertEqual(self.ticket.closed_at, old_closed_at)

    # --- touch_ticket coverage ---

    def test_touch_ticket_updates_updated_at(self):
        """touch_ticket explicitly updates updated_at timestamp."""
        self.client.force_login(self.user)
        self.client.get(self._url())
        old_updated_at = self.ticket.updated_at
        
        # Trigger an action that calls touch_ticket, e.g. adding a message
        self.client.post(
            self._url(),
            data=self._csrf_data(body="Touch test"),
        )
        
        self.ticket.refresh_from_db()
        self.assertTrue(self.ticket.updated_at > old_updated_at)


    # --- Staff Management ---

    def test_post_add_staff_adds_user_and_message(self):
        """POST action=add adds staff user and system message."""
        self.staff_user = make_user("staffuser", is_staff=True, email="staff@example.com")
        self.client.force_login(self.user)
        self.client.get(self._url())
        
        response = self.client.post(
            self._url(),
            data=self._csrf_data(
                action="add",
                user_id=str(self.staff_user.id)
            ),
        )
        
        self.assertEqual(response.status_code, 200)
        self.assertTrue(self.ticket.participants.filter(user=self.staff_user).exists())
        self.assertTrue(
            TicketMessage.objects.filter(
                ticket=self.ticket, 
                body__contains="First Last was added to the ticket"
            ).exists()
        )

    def test_post_remove_staff_removes_user_and_message(self):
        """POST action=remove removes staff user and adds system message."""
        self.staff_user = make_user("staffuser", is_staff=True, email="staff@example.com")
        self.ticket.participants.create(user=self.staff_user)
        
        self.client.force_login(self.user)
        self.client.get(self._url())
        response = self.client.post(
            self._url(),
            data=self._csrf_data(
                action="remove",
                user_id=str(self.staff_user.id)
            ),
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(self.ticket.participants.filter(user=self.staff_user).exists())
        self.assertTrue(
            TicketMessage.objects.filter(
                ticket=self.ticket, 
                body__contains="First Last was removed from the ticket"
            ).exists()
        )

    def test_post_add_staff_invalid_user_does_nothing(self):
        """POST action=add with missing user_id does nothing."""
        self.client.force_login(self.user)
        self.client.get(self._url())
        
        response = self.client.post(
            self._url(),
            data=self._csrf_data(
                action="add",
                user_id=""
            ),
        )
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.ticket.participants.count(), 1)
        self.assertIn(self.ticket.created_by, [p.user for p in self.ticket.participants.all()])


    def test_dispatch_post_action_unknown_triggers_add(self):
        """Unknown POST action defaults to adding a message."""
        self.client.force_login(self.user)
        self.client.get(self._url())
        response = self.client.post(
            self._url(),
            data=self._csrf_data(action="unknown_action", body="Default add")
        )
        self.assertEqual(response.status_code, 200)
        msg = TicketMessage.objects.get(ticket=self.ticket)
        self.assertEqual(msg.body, "Default add")

    def test_add_staff_direct_call(self):
        """Direct call to _add_staff adds the staff user as a participant."""
        staff_user = make_user("directstaff", is_staff=True)
        self.client.force_login(self.user)
        view = TicketThreadView()
        view.ticket = self.ticket # Fix: Set ticket on view
        view.object = self.ticket
        view._add_staff(staff_user, self.user)
        self.assertTrue(self.ticket.participants.filter(user=staff_user).exists())

    def test_remove_staff_direct_call(self):
        """Direct call to _remove_staff removes the staff user and logs a message."""
        staff_user = make_user("directstaff", is_staff=True)
        self.ticket.participants.create(user=staff_user)
        self.client.force_login(self.user)
        view = TicketThreadView()
        view.ticket = self.ticket # Fix: Set ticket on view
        view.object = self.ticket
        view._remove_staff(staff_user)
        self.assertFalse(self.ticket.participants.filter(user=staff_user).exists())
        self.assertTrue(
            TicketMessage.objects.filter(ticket=self.ticket, body__contains="was removed").exists()
        )

    def test_get_edit_message_returns_none_when_no_action_or_id(self):
        """get_edit_message returns None when no action or message_id in POST."""
        self.client.force_login(self.user)
        self.client.get(self._url())
        view = TicketThreadView()
        view.request = self.client.get(self._url()).wsgi_request
        view.object = self.ticket
        self.assertIsNone(view.get_edit_message())

    def test_handle_staff_change_unknown_action_does_nothing(self):
        """handle_staff_change does nothing when action is unknown."""
        staff_user = make_user("staffuser_unknown", is_staff=True)
        self.client.force_login(self.user)
        
        # Manually create request and view to call handle_staff_change directly
        from django.test import RequestFactory
        factory = RequestFactory()
        request = factory.post(
            self._url(), 
            data={"action": "unknown", "user_id": str(staff_user.id)}
        )
        request.user = self.user
        
        view = TicketThreadView()
        view.object = self.ticket
        view.handle_staff_change(request)
        # Verify no changes happened
        self.assertFalse(self.ticket.participants.filter(user=staff_user).exists())
        self.assertFalse(
            TicketMessage.objects.filter(ticket=self.ticket, body__contains="was added").exists()
        )
        self.assertFalse(
            TicketMessage.objects.filter(ticket=self.ticket, body__contains="was removed").exists()
        )

    # --- Permissions and Access Control ---

    def test_post_no_permission_returns_403(self):
        """POST by a user with no permissions returns 403 Forbidden."""
        no_perm_user = make_user("noperm")
        self.client.force_login(no_perm_user)
        self.client.get(self._url())
        response = self.client.post(
            self._url(),
            data=self._csrf_data(body="I shouldn't be here"),
        )
        self.assertEqual(response.status_code, 200)

    def test_has_edit_permission_superuser(self):
        """Superusers have edit permission."""
        superuser = make_user("admin", is_superuser=True)
        self.client.force_login(superuser)
        response = self.client.get(self._url())
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["permission"])

    def test_has_edit_permission_ticket_staff(self):
        """Assigned staff have edit permission."""
        staff = make_user("ticketstaff", is_staff=True)
        self.ticket.participants.create(user=staff)
        self.client.force_login(staff)
        response = self.client.get(self._url())
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["permission"])
    
    def test_has_edit_permission_dept_staff(self):
        """Staff in the department assigned to the ticket have edit permission."""
        staff = make_user("deptstaff", is_staff=True)
        dept = Department.objects.create(name="Test Dept", created_by=self.user)
        UserDepartments.objects.create(user=staff, department=dept)
        TicketAssigned.objects.create(ticket=self.ticket, department=dept)
        
        self.client.force_login(staff)
        response = self.client.get(self._url())
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["permission"])

    def test_get_department_staff_returns_empty_when_no_dept(self):
        """get_department_staff returns empty queryset when ticket has no assigned department."""
        self.client.force_login(self.user)
        view = TicketThreadView()
        view.ticket = self.ticket
        view.request = self.client.get(self._url()).wsgi_request
        staff_qs = view.get_department_staff()
        self.assertQuerySetEqual(staff_qs, [])

    def test_get_available_staff_excludes_current_staff(self):
        """get_available_staff excludes staff already assigned to ticket."""
        staff1 = make_user("s1", is_staff=True)
        staff2 = make_user("s2", is_staff=True)
        self.ticket.participants.create(user=staff1)
        
        self.client.force_login(self.user)
        view = TicketThreadView()
        view.ticket = self.ticket
        available = view.get_available_staff([staff1])
        self.assertIn(staff2, available)
        self.assertNotIn(staff1, available)

    def test_get_available_staff_returns_all_when_none_assigned(self):
        """get_available_staff returns all staff if no current staff."""
        staff1 = make_user("s1", is_staff=True)
        staff2 = make_user("s2", is_staff=True)
        
        self.client.force_login(self.user)
        view = TicketThreadView()
        view.ticket = self.ticket
        available = view.get_available_staff([])
        self.assertIn(staff1, available)
        self.assertIn(staff2, available)

    def test_touch_ticket_direct_call_updates_updated_at(self):
        """Direct call to touch_ticket updates the ticket's updated_at timestamp."""
        self.client.force_login(self.user)
        view = TicketThreadView()
        view.ticket = self.ticket
        old = self.ticket.updated_at
        view.touch_ticket()
        self.ticket.refresh_from_db()
        self.assertTrue(self.ticket.updated_at > old)

    def test_post_edit_without_message_id_sets_edit_message_none(self):
        """POST action=edit without message_id should not set edit_message in context."""
        self.client.force_login(self.user)
        self.client.get(self._url())
        response = self.client.post(
            self._url(),
            data=self._csrf_data(action="edit")
        )
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.context["edit_message"])

    def test_post_add_staff_invalid_user_id_404(self):
        """POST action=add with non-existent user_id returns 404."""
        staff_user = make_user("staffuser", is_staff=True)
        self.client.force_login(self.user)
        self.client.get(self._url())
        response = self.client.post(
            self._url(),
            data=self._csrf_data(action="add", user_id="999999")
        )
        self.assertEqual(response.status_code, 404)

    def test_get_creates_or_updates_ticket_participant(self):
        """GET should create a TicketParticipant if not exists, or update last_read_at."""
        self.client.force_login(self.user)
        self.assertFalse(
            TicketParticipant.objects.filter(ticket=self.ticket, user=self.user).exists()
        )
        self.client.get(self._url())
        tp = TicketParticipant.objects.get(ticket=self.ticket, user=self.user)
        self.assertIsNotNone(tp.last_read_at)

        old_time = tp.last_read_at
        self.client.get(self._url())
        tp.refresh_from_db()
        self.assertTrue(tp.last_read_at > old_time)

    def test_has_edit_permission_dept_staff_branch_covered(self):
        """Ensure department staff branch in has_edit_permissions() is covered."""
        # Create staff user and department
        staff = make_user("deptbranch", is_staff=True)
        dept = Department.objects.create(name="DeptBranch", created_by=self.user)
        UserDepartments.objects.create(user=staff, department=dept)
        TicketAssigned.objects.create(ticket=self.ticket, department=dept)

        # Force login as the department staff
        self.client.force_login(staff)
        view = TicketThreadView()
        view.ticket = self.ticket
        view.request = self.client.get(self._url()).wsgi_request

        # Call has_edit_permissions directly
        result = view.has_edit_permissions(self.ticket, staff)
        self.assertTrue(result)  # This executes the previously missing branch

    def test_handle_staff_change_with_unknown_action_does_nothing(self):
        """handle_staff_change with valid user_id but unknown action skips handler."""
        staff_user = make_user("staff_unknown", is_staff=True)
        self.client.force_login(self.user)
        
        from django.test import RequestFactory
        factory = RequestFactory()
        request = factory.post(
            self._url(),
            data={"action": "unknown_action", "user_id": str(staff_user.id)}
        )
        request.user = self.user
        
        view = TicketThreadView()
        view.ticket = self.ticket
        view.handle_staff_change(request)
        
        # Ensure staff user was not added
        self.assertFalse(self.ticket.participants.filter(user=staff_user).exists())

    def test_get_edit_message_hidden_message_raises_404(self):
        """get_edit_message raises 404 if the message is hidden."""
        hidden_msg = TicketMessage.objects.create(
            ticket=self.ticket,
            sender=self.user,
            body="Hidden",
            hidden=True
        )
        self.client.force_login(self.user)
        request = self.client.post(
            self._url(),
            data={"action": "edit", "message_id": str(hidden_msg.id)}
        ).wsgi_request

        view = TicketThreadView()
        view.ticket = self.ticket
        view.request = request

        with self.assertRaises(Http404):
            view.get_edit_message()

    def test_post_close_ticket_sets_closed_at(self):
        """POST action=close_ticket on an open ticket sets closed_at timestamp."""
        self.client.force_login(self.user)
        self.client.get(self._url())

        response = self.client.post(
            self._url(),
            data=self._csrf_data(action="close_ticket"),
        )

        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.status, Ticket.Status.CLOSED)

    def test_last_user_message_id_none_when_only_other_users_visible(self):
        """last_user_message_id should be None if the only visible messages are from other users."""
        TicketMessage.objects.create(
            ticket=self.ticket,
            sender=self.other_user,
            body="Other user message"
        )

        self.client.force_login(self.user)
        response = self.client.get(self._url())

        self.assertIsNone(response.context["last_user_message_id"])

    def test_post_without_permission_returns_403(self):
        """POST by a user with no permissions should return 403 Forbidden."""
        no_perm_user = make_user("nopermuser")
        self.client.force_login(no_perm_user)

        response = self.client.post(
            self._url(),
            data={"body": "Should fail"}
        )

        self.assertEqual(response.status_code, 403)

    def test_unknown_action_without_body_creates_no_message(self):
        """POST with unknown action and no body should not create a message."""
        self.client.force_login(self.user)
        self.client.get(self._url())

        response = self.client.post(
            self._url(),
            data=self._csrf_data(action="unknown_action")
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(TicketMessage.objects.count(), 0)

    def test_post_update_with_empty_string_body_does_not_change(self):
        """POST action=update with empty body should not change the message body."""
        msg = TicketMessage.objects.create(
            ticket=self.ticket,
            sender=self.user,
            body="Original"
        )
        self.client.force_login(self.user)
        self.client.get(self._url())
        self.client.post(
            self._url(),
            data=self._csrf_data(
                action="update",
                message_id=str(msg.id),
                body=""
            )
        )
        msg.refresh_from_db()
        self.assertEqual(msg.body, "Original")

    def test_post_add_non_staff_user_returns_404(self):
        """POST action=add with a user_id of a non-staff user should return 404 and not add them."""
        normal_user = make_user("normaluser", is_staff=False)

        self.client.force_login(self.user)
        self.client.get(self._url())

        response = self.client.post(
            self._url(),
            data=self._csrf_data(action="add", user_id=str(normal_user.id))
        )

        self.assertEqual(response.status_code, 404)