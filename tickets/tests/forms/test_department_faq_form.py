from django.test import TestCase

from tickets.forms import DepartmentFAQForm


class DepartmentFAQFormTests(TestCase):
    """Tests for DepartmentFAQForm."""

    def test_valid_form(self):
        """Form is valid when both question and answer are provided."""
        form = DepartmentFAQForm(data={"question": "What is NAC?", "answer": "A ticketing system."})
        self.assertTrue(form.is_valid())

    def test_missing_question(self):
        """Form is invalid when question is blank."""
        form = DepartmentFAQForm(data={"question": "", "answer": "Some answer."})
        self.assertFalse(form.is_valid())
        self.assertIn("question", form.errors)

    def test_missing_answer(self):
        """Form is invalid when answer is blank."""
        form = DepartmentFAQForm(data={"question": "A question?", "answer": ""})
        self.assertFalse(form.is_valid())
        self.assertIn("answer", form.errors)

    def test_both_fields_missing(self):
        """Form is invalid when both fields are blank."""
        form = DepartmentFAQForm(data={"question": "", "answer": ""})
        self.assertFalse(form.is_valid())
        self.assertIn("question", form.errors)
        self.assertIn("answer", form.errors)

    def test_widgets_have_correct_css_classes(self):
        """Widgets carry the expected CSS classes."""
        form = DepartmentFAQForm()
        self.assertIn("department-form-input", form.fields["question"].widget.attrs["class"])
        self.assertIn("department-form-textarea", form.fields["answer"].widget.attrs["class"])
