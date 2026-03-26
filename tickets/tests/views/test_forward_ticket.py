from urllib.parse import unquote

from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model

from tickets.models import Ticket
from tickets.models.notification import Notification
from tickets.models.ticket_participant import TicketParticipant
from tickets.views.forward_ticket_view import _err, _ticket_redirect

from types import SimpleNamespace

User = get_user_model()


class ForwardTicketViewTests(TestCase):
    """Tests for forwarding tickets to staff."""

    def setUp(self):
        """Prepare users, ticket, and URL used by the forward ticket tests."""
        self.client = Client()
        self.forward_url_name = "ticket_forward"
        mapping = [
            ("student", False, "Stu", "Dent"),
            ("teacher1", True, "Tea", "Cher1"),
            ("teacher2", True, "Tea", "Cher2"),
        ]
        for attr, is_staff, fname, lname in mapping:
            u = User.objects.create_user(username=attr, password="pass12345",
                                         email=f"{attr}@example.com", first_name=fname, last_name=lname,
                                         is_staff=is_staff)
            setattr(self, attr if attr=="student" else attr.replace("teacher","staff"), u)
        # keep attribute names used by tests: self.student, self.staff1, self.staff2
        self.student = getattr(self, 'student')
        self.staff1 = getattr(self, 'staff1') if hasattr(self, 'staff1') else User.objects.get(username='teacher1')
        self.staff2 = getattr(self, 'staff2') if hasattr(self, 'staff2') else User.objects.get(username='teacher2')
        self.ticket = Ticket.objects.create(title="Forward me", created_by=self.student,
                                            status=getattr(Ticket.Status, "OPEN", "open"))
        self.url = reverse(self.forward_url_name, args=[self.ticket.uuid])

    # ---------- helpers ----------

    def login(self, user):
        """Force-login the given user into the test client."""
        self.client.force_login(user)

    def post(self, user=None, **data):
        """Helper to POST to the forward URL optionally as `user`."""
        if user is not None:
            self.login(user)
        return self.client.post(self.url, data=data)

    def loc(self, response):
        """Assert response is a redirect and return its Location header."""
        self.assertEqual(response.status_code, 302)
        return response["Location"]

    def assert_loc_has(self, response, *parts):
        """Assert that the redirect location contains the given parts."""
        loc = self.loc(response)
        for p in parts:
            self.assertIn(p, loc)
        return loc

    def decoded(self, response):
        """Return URL-decoded redirect Location for easier assertions."""
        return unquote(self.loc(response))

    def participant(self):
        """Return the TicketParticipant record for the forwarded staff2 user."""
        return TicketParticipant.objects.get(ticket=self.ticket, user=self.staff2)

    # ------------------ tests ------------------

    def test_requires_authenticated(self):
        """Anonymous POST should be forbidden with a permission error message."""
        resp = self.client.post(self.url, data={"email": self.staff2.email})
        self.assertEqual(resp.status_code, 302)

    def test_requires_staff(self):
        """Non-staff users should receive 403 when attempting to forward."""
        resp = self.post(self.student, email=self.staff2.email)
        self.assertEqual(resp.status_code, 403)

    def test_invalid_missing_email_goes_err(self):
        """Missing email parameter should redirect with an error status."""
        resp = self.post(self.staff1, return_tab="active")
        self.assert_loc_has(
            resp, "/?tab=active", f"open={self.ticket.uuid}",
            "fwd=err", f"tid={self.ticket.uuid}", "msg="
        )

    def test_email_not_found_goes_err_with_msg(self):
        """Unknown email should redirect with an explanatory error message."""
        resp = self.post(self.staff1, email="nope@example.com", return_tab="overdue")
        self.assert_loc_has(resp, "/?tab=overdue", "fwd=err", "msg=")
        self.assertIn("No user found", self.decoded(resp))

    def test_email_exists_but_not_staff_goes_err(self):
        """Forwarding to a non-staff user should produce an error."""
        resp = self.post(self.staff1, email=self.student.email, return_tab="completed")
        self.assert_loc_has(resp, "/?tab=completed", "fwd=err", "msg=")
        self.assertIn("not a staff member", self.decoded(resp))

    def test_cannot_forward_to_self(self):
        """Users should not be able to forward a ticket to themselves."""
        resp = self.post(self.staff1, email=self.staff1.email, return_tab="active")
        self.assert_loc_has(resp, "/?tab=active", "fwd=err", "msg=")
        self.assertIn("cannot forward", self.decoded(resp).lower())

    def test_success_creates_participant_and_ok_redirect(self):
        """Successful forward should create a TicketParticipant and redirect with ok."""
        resp = self.post(self.staff1, email=self.staff2.email, return_tab="active")
        self.assert_loc_has(resp, "/?tab=active", "fwd=ok", f"tid={self.ticket.uuid}", "email=")
        self.assertTrue(TicketParticipant.objects.filter(ticket=self.ticket, user=self.staff2).exists())
        self.assertIn(self.staff2.email, self.decoded(resp))

    def test_forward_is_idempotent(self):
        """Forwarding the same staff twice should not create duplicate participants."""
        self.post(self.staff1, email=self.staff2.email, return_tab="active")
        self.post(self.staff1, email=self.staff2.email, return_tab="active")
        qs = TicketParticipant.objects.filter(ticket=self.ticket, user=self.staff2)
        self.assertEqual(qs.count(), 1)

    def test_sets_added_by_when_field_exists(self):
        """When TicketParticipant has added_by field, it should be set to the forwarder."""
        self.post(self.staff1, email=self.staff2.email, return_tab="active")
        tp = self.participant()
        self.assertTrue(hasattr(tp, "added_by"))
        self.assertEqual(tp.added_by, self.staff1)

    def test_return_tab_defaults_to_active(self):
        """If no return_tab is provided, redirect defaults to the 'active' tab."""
        resp = self.post(self.staff1, email=self.staff2.email)
        self.assert_loc_has(resp, "/?tab=active", "fwd=ok")

    def test_ticket_not_found_returns_404(self):
        """Forwarding a non-existent ticket UUID should return 404."""
        fake_url = reverse(self.forward_url_name, args=["00000000-0000-0000-0000-000000000000"])
        self.login(self.staff1)
        resp = self.client.post(fake_url, data={"email": self.staff2.email})
        self.assertEqual(resp.status_code, 404)

    def test_ticket_redirect_with_no_params(self):
        """_ticket_redirect should redirect even when no params are given."""
        resp = _ticket_redirect("active", self.ticket.uuid)
        self.assertEqual(resp.status_code, 302)
        self.assertIn(f"/?tab=active&open={self.ticket.uuid}", resp["Location"])
    
    def test_err_falls_back_when_no_email_error(self):
        """_err should fall back to default message if no email error exists."""
        form = SimpleNamespace(errors={})
        self.assertEqual(_err(form), "Email failed to forward.")

    def test_forward_creates_ticket_forwarded_notification(self):
        """Successful forward should create a TICKET_FORWARDED notification for the target user."""
        resp = self.post(self.staff1, email=self.staff2.email, return_tab="active")
        self.assertEqual(resp.status_code, 302)
        notifications = Notification.objects.filter(
            user=self.staff2,
            notification_type=Notification.NotificationType.TICKET_FORWARDED,
        )
        self.assertEqual(notifications.count(), 1)
        self.assertEqual(notifications[0].actor, self.staff1)
        self.assertEqual(notifications[0].target_object, self.ticket)

    def test_forward_notification_not_created_on_invalid(self):
        """No notification should be created if the forward is invalid (e.g., self-forward)."""
        self.post(self.staff1, email=self.staff1.email, return_tab="active")
        notifications = Notification.objects.filter(
            notification_type=Notification.NotificationType.TICKET_FORWARDED,
        )
        self.assertEqual(notifications.count(), 0)
