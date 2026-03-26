from django.test import TestCase
from django.http import Http404
from django.contrib.auth import get_user_model

from tickets.forms import DepartmentFAQForm
from tickets.models import Department, DepartmentFAQ

User = get_user_model()


class DepartmentFAQModelTests(TestCase):
    """Tests for the DepartmentFAQ model."""

    def setUp(self):
        """Set up a creator user and department for FAQ tests."""
        self.creator = User.objects.create_user(
            username="creator", email="creator@e.com", password="p", is_staff=True
        )
        self.dept = Department.objects.create(name="Support", created_by=self.creator)

    def _make_faq(self, question="How do I reset my password?", answer="Click forgot password.", **kwargs):
        """Create and return a DepartmentFAQ with sensible defaults."""
        return DepartmentFAQ.objects.create(
            department=self.dept,
            question=question,
            answer=answer,
            created_by=self.creator,
            **kwargs,
        )

    def test_creation_and_str(self):
        """FAQ is created correctly and __str__ returns department: question snippet."""
        faq = self._make_faq()
        self.assertIsInstance(faq, DepartmentFAQ)
        self.assertIn("Support", str(faq))
        self.assertIn("How do I reset", str(faq))

    def test_str_truncates_long_question(self):
        """__str__ truncates question to 60 chars."""
        long_q = "A" * 80
        faq = self._make_faq(question=long_q)
        self.assertLessEqual(len(str(faq).split(": ", 1)[1]), 60)

    def test_default_order_field(self):
        """order defaults to 0."""
        faq = self._make_faq()
        self.assertEqual(faq.order, 0)

    def test_ordering_by_order_then_created_on(self):
        """FAQs are ordered by order ascending, then created_on ascending."""
        faq_b = self._make_faq(question="B", order=2)
        faq_a = self._make_faq(question="A", order=1)
        faq_c = self._make_faq(question="C", order=2)
        qs = list(DepartmentFAQ.objects.all())
        self.assertEqual(qs[0], faq_a)
        self.assertEqual(qs[1], faq_b)
        self.assertEqual(qs[2], faq_c)

    def test_cascade_delete_with_department(self):
        """Deleting department cascades to FAQs."""
        self._make_faq()
        self.dept.delete()
        self.assertEqual(DepartmentFAQ.objects.count(), 0)

    def test_created_by_set_null_on_user_delete(self):
        """Deleting the creator sets created_by to NULL, FAQ survives."""
        other = User.objects.create_user(username="other", email="o@e.com", password="p")
        faq = DepartmentFAQ.objects.create(
            department=self.dept, question="Q", answer="A", created_by=other
        )
        other.delete()
        faq.refresh_from_db()
        self.assertIsNone(faq.created_by)
        self.assertEqual(DepartmentFAQ.objects.count(), 1)

    def test_faqs_related_name(self):
        """Department.faqs reverse relation works."""
        self._make_faq()
        self._make_faq(question="Another question?")
        self.assertEqual(self.dept.faqs.count(), 2)

    def test_create_from_form_sets_department_and_creator(self):
        """create_from_form should persist a faq with department and actor."""
        form = DepartmentFAQForm(data={"question": "Q", "answer": "A"})

        self.assertTrue(form.is_valid())
        faq = DepartmentFAQ.create_from_form(form, department=self.dept, actor=self.creator)

        self.assertEqual(faq.department, self.dept)
        self.assertEqual(faq.created_by, self.creator)

    def test_update_from_form_saves_changes(self):
        """update_from_form should save a bound FAQ form."""
        faq = self._make_faq()
        form = DepartmentFAQForm(
            data={"question": "Updated", "answer": "Changed"},
            instance=faq,
        )

        self.assertTrue(form.is_valid())
        updated = DepartmentFAQ.update_from_form(form)

        self.assertEqual(updated.question, "Updated")
        self.assertEqual(updated.answer, "Changed")

    def test_get_for_department_or_404_is_scoped(self):
        """get_for_department_or_404 should only resolve FAQs in the department."""
        faq = self._make_faq()
        other = Department.objects.create(name="Other", created_by=self.creator)

        resolved = DepartmentFAQ.get_for_department_or_404(
            faq_id=faq.id,
            department=self.dept,
        )

        self.assertEqual(resolved, faq)
        with self.assertRaises(Http404):
            DepartmentFAQ.get_for_department_or_404(faq_id=faq.id, department=other)

    def test_delete_for_department_checks_membership(self):
        """delete_for_department should only delete when the department matches."""
        faq = self._make_faq(question="Delete me")
        other = Department.objects.create(name="Mismatch", created_by=self.creator)

        self.assertFalse(faq.delete_for_department(other))
        self.assertTrue(DepartmentFAQ.objects.filter(pk=faq.pk).exists())
        self.assertTrue(faq.delete_for_department(self.dept))
        self.assertFalse(DepartmentFAQ.objects.filter(pk=faq.pk).exists())
