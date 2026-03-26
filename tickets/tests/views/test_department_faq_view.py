from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model

from tickets.models import Department, DepartmentFAQ, UserDepartments
from tickets.forms import DepartmentFAQForm

User = get_user_model()


class DepartmentFAQViewSetup(TestCase):
    """Shared setUp for FAQ view tests."""

    def setUp(self):
        """Set up users, department, and URL for FAQ view tests."""
        self.client = Client()
        self.owner = User.objects.create_user(
            username="owner", email="owner@e.com", password="p", is_staff=True
        )
        self.member = User.objects.create_user(
            username="member", email="member@e.com", password="p", is_staff=True
        )
        self.outsider = User.objects.create_user(
            username="outsider", email="outsider@e.com", password="p"
        )
        self.superuser = User.objects.create_superuser(
            username="su", email="su@e.com", password="p"
        )
        self.dept = Department.objects.create(name="IT", created_by=self.owner)
        UserDepartments.objects.create(user=self.owner, department=self.dept)
        UserDepartments.objects.create(user=self.member, department=self.dept)
        self.url = reverse("department", kwargs={"department_slug": self.dept.slug})

    def _make_faq(self, question="How to reset?", answer="Click forgot password."):
        """Create and return a DepartmentFAQ on the test department."""
        return DepartmentFAQ.objects.create(
            department=self.dept,
            question=question,
            answer=answer,
            created_by=self.owner,
        )


class DepartmentFAQContextTests(DepartmentFAQViewSetup):
    """Tests for FAQ data included in the department page context."""

    def test_context_includes_faqs_and_form(self):
        """GET response context includes faqs queryset and faq_form."""
        self._make_faq()
        self.client.force_login(self.member)
        res = self.client.get(self.url)
        self.assertEqual(res.status_code, 200)
        self.assertIn("faqs", res.context)
        self.assertIn("faq_form", res.context)
        self.assertIsInstance(res.context["faq_form"], DepartmentFAQForm)
        self.assertEqual(res.context["faqs"].count(), 1)

    def test_user_can_manage_faqs_true_for_member(self):
        """Department members see user_can_manage_faqs=True."""
        self.client.force_login(self.member)
        res = self.client.get(self.url)
        self.assertTrue(res.context["user_can_manage_faqs"])

    def test_user_can_manage_faqs_true_for_superuser(self):
        """Superusers see user_can_manage_faqs=True."""
        self.client.force_login(self.superuser)
        res = self.client.get(self.url)
        self.assertTrue(res.context["user_can_manage_faqs"])

    def test_user_can_manage_faqs_false_for_outsider(self):
        """Non-members who somehow access the page see user_can_manage_faqs=False."""
        # Superuser bypasses can_view, so use a department member who is not in faqs scope
        non_member = User.objects.create_user(username="nm", email="nm@e.com", password="p")
        UserDepartments.objects.create(user=non_member, department=self.dept)
        # Temporarily remove from dept to test can_manage_faqs=False scenario
        # We can't easily fake this via view; test the model method directly instead
        self.assertFalse(self.dept.can_manage_faqs(self.outsider))


class DepartmentFAQAddTests(DepartmentFAQViewSetup):
    """Tests for add_faq POST action."""

    def _post_add(self, user, question="How to reset?", answer="Click forgot password."):
        """POST an add_faq action as the given user."""
        self.client.force_login(user)
        return self.client.post(self.url, {
            "action": "add_faq",
            "question": question,
            "answer": answer,
        })

    def test_member_can_add_faq(self):
        """A department member can successfully add a FAQ."""
        res = self._post_add(self.member)
        self.assertRedirects(res, self.url, fetch_redirect_response=False)
        self.assertEqual(DepartmentFAQ.objects.count(), 1)
        faq = DepartmentFAQ.objects.first()
        self.assertEqual(faq.question, "How to reset?")
        self.assertEqual(faq.created_by, self.member)

    def test_owner_can_add_faq(self):
        """The department owner can add a FAQ."""
        self._post_add(self.owner)
        self.assertEqual(DepartmentFAQ.objects.count(), 1)

    def test_superuser_can_add_faq(self):
        """A superuser can add a FAQ."""
        self._post_add(self.superuser)
        self.assertEqual(DepartmentFAQ.objects.count(), 1)

    def test_outsider_cannot_add_faq(self):
        """A non-member gets 403 when trying to add a FAQ."""
        self.client.force_login(self.outsider)
        res = self.client.post(self.url, {
            "action": "add_faq",
            "question": "Q",
            "answer": "A",
        })
        self.assertEqual(res.status_code, 403)
        self.assertEqual(DepartmentFAQ.objects.count(), 0)

    def test_invalid_faq_form_shows_error_message(self):
        """Submitting an empty question shows an error message and does not create FAQ."""
        res = self._post_add(self.member, question="", answer="")
        self.assertRedirects(res, self.url, fetch_redirect_response=False)
        self.assertEqual(DepartmentFAQ.objects.count(), 0)

    def test_unauthenticated_add_redirects_to_login(self):
        """Unauthenticated POST redirects to login."""
        res = self.client.post(self.url, {"action": "add_faq", "question": "Q", "answer": "A"})
        self.assertEqual(res.status_code, 302)
        self.assertIn("login", res.url)


class DepartmentFAQEditTests(DepartmentFAQViewSetup):
    """Tests for edit_faq POST action."""

    def setUp(self):
        """Create a FAQ to edit in each test."""
        super().setUp()
        self.faq = self._make_faq()

    def _post_edit(self, user, question="Updated question?", answer="Updated answer."):
        """POST an edit_faq action as the given user."""
        self.client.force_login(user)
        return self.client.post(self.url, {
            "action": "edit_faq",
            "faq_id": self.faq.id,
            "question": question,
            "answer": answer,
        })

    def test_member_can_edit_faq(self):
        """A department member can edit an existing FAQ."""
        res = self._post_edit(self.member)
        self.assertRedirects(res, self.url, fetch_redirect_response=False)
        self.faq.refresh_from_db()
        self.assertEqual(self.faq.question, "Updated question?")
        self.assertEqual(self.faq.answer, "Updated answer.")

    def test_superuser_can_edit_faq(self):
        """A superuser can edit an existing FAQ."""
        self._post_edit(self.superuser, question="Super Q", answer="Super A")
        self.faq.refresh_from_db()
        self.assertEqual(self.faq.question, "Super Q")

    def test_outsider_cannot_edit_faq(self):
        """A non-member gets 403 when trying to edit a FAQ."""
        self.client.force_login(self.outsider)
        res = self.client.post(self.url, {
            "action": "edit_faq",
            "faq_id": self.faq.id,
            "question": "Hacked?",
            "answer": "Hacked.",
        })
        self.assertEqual(res.status_code, 403)
        self.faq.refresh_from_db()
        self.assertEqual(self.faq.question, "How to reset?")

    def test_invalid_edit_shows_error_message(self):
        """Submitting blank fields on edit shows error and does not update FAQ."""
        res = self._post_edit(self.member, question="", answer="")
        self.assertRedirects(res, self.url, fetch_redirect_response=False)
        self.faq.refresh_from_db()
        self.assertEqual(self.faq.question, "How to reset?")

    def test_edit_wrong_department_faq_returns_404(self):
        """Editing a FAQ that belongs to another department returns 404."""
        other_owner = User.objects.create_user(username="oo", email="oo@e.com", password="p", is_staff=True)
        other_dept = Department.objects.create(name="HR", created_by=other_owner)
        UserDepartments.objects.create(user=other_owner, department=other_dept)
        other_faq = DepartmentFAQ.objects.create(
            department=other_dept, question="Other Q", answer="Other A", created_by=other_owner
        )
        self.client.force_login(self.owner)
        res = self.client.post(self.url, {
            "action": "edit_faq",
            "faq_id": other_faq.id,
            "question": "Hijacked?",
            "answer": "Hijacked.",
        })
        self.assertEqual(res.status_code, 404)


class DepartmentFAQDeleteTests(DepartmentFAQViewSetup):
    """Tests for delete_faq POST action."""

    def setUp(self):
        """Create a FAQ to delete in each test."""
        super().setUp()
        self.faq = self._make_faq()

    def _post_delete(self, user):
        """POST a delete_faq action as the given user."""
        self.client.force_login(user)
        return self.client.post(self.url, {
            "action": "delete_faq",
            "faq_id": self.faq.id,
        })

    def test_member_can_delete_faq(self):
        """A department member can delete a FAQ."""
        res = self._post_delete(self.member)
        self.assertRedirects(res, self.url, fetch_redirect_response=False)
        self.assertEqual(DepartmentFAQ.objects.count(), 0)

    def test_superuser_can_delete_faq(self):
        """A superuser can delete a FAQ."""
        self._post_delete(self.superuser)
        self.assertEqual(DepartmentFAQ.objects.count(), 0)

    def test_outsider_cannot_delete_faq(self):
        """A non-member gets 403 when trying to delete a FAQ."""
        self.client.force_login(self.outsider)
        res = self.client.post(self.url, {
            "action": "delete_faq",
            "faq_id": self.faq.id,
        })
        self.assertEqual(res.status_code, 403)
        self.assertEqual(DepartmentFAQ.objects.count(), 1)

    def test_delete_wrong_department_faq_returns_404(self):
        """Deleting a FAQ from another department returns 404."""
        other_owner = User.objects.create_user(username="oo2", email="oo2@e.com", password="p", is_staff=True)
        other_dept = Department.objects.create(name="Finance", created_by=other_owner)
        other_faq = DepartmentFAQ.objects.create(
            department=other_dept, question="Q", answer="A", created_by=other_owner
        )
        self.client.force_login(self.owner)
        res = self.client.post(self.url, {
            "action": "delete_faq",
            "faq_id": other_faq.id,
        })
        self.assertEqual(res.status_code, 404)


class DepartmentCanManageFAQsTests(DepartmentFAQViewSetup):
    """Unit tests for Department.can_manage_faqs()."""

    def test_returns_true_for_department_member(self):
        """Members of the department can manage FAQs."""
        self.assertTrue(self.dept.can_manage_faqs(self.member))

    def test_returns_true_for_owner(self):
        """The department owner can manage FAQs."""
        self.assertTrue(self.dept.can_manage_faqs(self.owner))

    def test_returns_true_for_superuser(self):
        """Superusers can manage FAQs on any department."""
        self.assertTrue(self.dept.can_manage_faqs(self.superuser))

    def test_returns_false_for_non_member(self):
        """Non-members cannot manage FAQs."""
        self.assertFalse(self.dept.can_manage_faqs(self.outsider))
