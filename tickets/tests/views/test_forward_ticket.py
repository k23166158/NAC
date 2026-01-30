# tickets/tests/views/test_forward_ticket.py
from urllib.parse import unquote

from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model

from tickets.models import Ticket
from tickets.models.ticket_participant import TicketParticipant

User = get_user_model()


class ForwardTicketViewTests(TestCase):
    """Tests for forwarding tickets to staff."""

    def setUp(self):
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
        self.url = reverse(self.forward_url_name, args=[self.ticket.id])

    # ---------- helpers ----------

    def login(self, user):
        self.client.force_login(user)

    def post(self, user=None, **data):
        if user is not None:
            self.login(user)
        return self.client.post(self.url, data=data)

    def loc(self, response):
        self.assertEqual(response.status_code, 302)
        return response["Location"]

    def assert_loc_has(self, response, *parts):
        loc = self.loc(response)
        for p in parts:
            self.assertIn(p, loc)
        return loc

    def decoded(self, response):
        return unquote(self.loc(response))

    def participant(self):
        return TicketParticipant.objects.get(ticket=self.ticket, user=self.staff2)

    # ------------------ tests ------------------

    def test_requires_authenticated(self):
        resp = self.client.post(self.url, data={"email": self.staff2.email})
        self.assertEqual(resp.status_code, 403)
        self.assertIn("permission", resp.content.decode().lower())

    def test_requires_staff(self):
        resp = self.post(self.student, email=self.staff2.email)
        self.assertEqual(resp.status_code, 403)

    def test_invalid_missing_email_goes_err(self):
        resp = self.post(self.staff1, return_tab="active")
        self.assert_loc_has(
            resp, "/?tab=active", f"open={self.ticket.id}",
            "fwd=err", f"tid={self.ticket.id}", "msg="
        )

    def test_email_not_found_goes_err_with_msg(self):
        resp = self.post(self.staff1, email="nope@example.com", return_tab="overdue")
        self.assert_loc_has(resp, "/?tab=overdue", "fwd=err", "msg=")
        self.assertIn("No user found", self.decoded(resp))

    def test_email_exists_but_not_staff_goes_err(self):
        resp = self.post(self.staff1, email=self.student.email, return_tab="completed")
        self.assert_loc_has(resp, "/?tab=completed", "fwd=err", "msg=")
        self.assertIn("not a staff member", self.decoded(resp))

    def test_cannot_forward_to_self(self):
        resp = self.post(self.staff1, email=self.staff1.email, return_tab="active")
        self.assert_loc_has(resp, "/?tab=active", "fwd=err", "msg=")
        self.assertIn("cannot forward", self.decoded(resp).lower())

    def test_success_creates_participant_and_ok_redirect(self):
        resp = self.post(self.staff1, email=self.staff2.email, return_tab="active")
        self.assert_loc_has(resp, "/?tab=active", "fwd=ok", f"tid={self.ticket.id}", "email=")
        self.assertTrue(TicketParticipant.objects.filter(ticket=self.ticket, user=self.staff2).exists())
        self.assertIn(self.staff2.email, self.decoded(resp))

    def test_forward_is_idempotent(self):
        self.post(self.staff1, email=self.staff2.email, return_tab="active")
        self.post(self.staff1, email=self.staff2.email, return_tab="active")
        qs = TicketParticipant.objects.filter(ticket=self.ticket, user=self.staff2)
        self.assertEqual(qs.count(), 1)

    def test_sets_added_by_when_field_exists(self):
        self.post(self.staff1, email=self.staff2.email, return_tab="active")
        tp = self.participant()
        self.assertTrue(hasattr(tp, "added_by"))
        self.assertEqual(tp.added_by, self.staff1)

    def test_return_tab_defaults_to_active(self):
        resp = self.post(self.staff1, email=self.staff2.email)
        self.assert_loc_has(resp, "/?tab=active", "fwd=ok")
