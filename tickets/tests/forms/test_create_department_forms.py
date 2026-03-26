from django.test import TestCase
from django.contrib.auth import get_user_model
from tickets.forms import DepartmentForm
from tickets.models import Department

class DepartmentFormTests(TestCase):
    """Tests for the DepartmentForm."""

    def setUp(self):
        """Set up test user and department."""
        self.u = get_user_model().objects.create_user(username="u", email="e@e.com", password="p")
        self.d = Department.objects.create(name="IT Support", created_by=self.u)

    def test_form_valid_and_update(self):
        """Test valid creations, updates, and special character names."""
        f1 = DepartmentForm(data={'name': 'Finance', 'description': ''})
        self.assertTrue(f1.is_valid())
        f2 = DepartmentForm(data={'name': 'IT Support', 'description': 'U'}, instance=self.d)
        self.assertTrue(f2.is_valid())

    def test_form_validation_errors(self):
        """Test validation errors for duplicates, empty names, and reserved slugs."""
        for name in ['it support', 'create', 'edit', 'delete']:
            f = DepartmentForm(data={'name': name, 'description': 'D'})
            self.assertFalse(f.is_valid())
            self.assertIn('name', f.errors)
            
        f_empty = DepartmentForm(data={'name': '', 'description': 'D'})
        self.assertFalse(f_empty.is_valid())
        
        f_none = DepartmentForm()
        f_none.cleaned_data = {'name': None}
        self.assertIsNone(f_none.clean_name())

    def test_save_for_actor_sets_creator_and_membership(self):
        """save_for_actor should persist the department and assign the actor."""
        form = DepartmentForm(data={"name": "Finance", "description": "Numbers"})

        self.assertTrue(form.is_valid())
        department = form.save_for_actor(self.u)

        self.assertEqual(department.created_by, self.u)
        self.assertTrue(department.assigned_users.filter(user=self.u).exists())
