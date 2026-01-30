from django.test import TestCase
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model

from tickets.forms import CreateDepartmentForm
from tickets.models import Department

User = get_user_model()


class CreateDepartmentFormTests(TestCase):
    """Tests for the CreateDepartmentForm."""

    def setUp(self):
        """Set up a user for creating departments."""
        self.user = User.objects.create_user(
            username="creator",
            email="creator@example.com",
            password="pass12345",
            first_name="Test",
            last_name="User",
        )

    def test_form_with_valid_data(self):
        """Test that form accepts valid name and description."""
        form_data = {
            'name': 'IT Support',
            'description': 'Information Technology Support Department'
        }
        form = CreateDepartmentForm(data=form_data)
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data['name'], 'IT Support')
        self.assertEqual(form.cleaned_data['description'], 'Information Technology Support Department')

    def test_form_with_minimal_data(self):
        """Test that form accepts name without description."""
        form_data = {
            'name': 'Finance',
            'description': ''
        }
        form = CreateDepartmentForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_clean_name_raises_error_on_duplicate_name(self):
        """Test that clean_name raises ValidationError for duplicate department names."""
        Department.objects.create(
            name="IT Support",
            created_by=self.user
        )

        form_data = {
            'name': 'IT Support',
            'description': 'Another IT department'
        }
        form = CreateDepartmentForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('name', form.errors)
        self.assertIn(
            'A department with this name already exists. Please choose a different name.',
            form.errors['name']
        )

    def test_clean_name_case_insensitive_duplicate_detection(self):
        """Test that duplicate detection is case-insensitive via slug."""
        Department.objects.create(
            name="IT Support",
            created_by=self.user
        )

        form_data = {
            'name': 'it support',
            'description': 'Lowercase version'
        }
        form = CreateDepartmentForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('name', form.errors)

    def test_clean_name_allows_updating_existing_department(self):
        """Test that updating an existing department doesn't trigger false duplicate errors."""
        # Create an existing department
        department = Department.objects.create(
            name="IT Support",
            created_by=self.user
        )

        form_data = {
            'name': 'IT Support',
            'description': 'Updated description'
        }
        form = CreateDepartmentForm(data=form_data, instance=department)
        self.assertTrue(form.is_valid())

    def test_clean_name_handles_empty_name(self):
        """Test that clean_name handles empty name gracefully."""
        form_data = {
            'name': '',
            'description': 'Some description'
        }
        form = CreateDepartmentForm(data=form_data)
        self.assertFalse(form.is_valid())
        
    def test_clean_name_returns_empty_name_directly(self):
        """Test that clean_name returns early when name is empty/None."""
        # Test clean_name directly to cover the early return path
        form = CreateDepartmentForm()
        form.cleaned_data = {'name': ''}
        result = form.clean_name()
        self.assertEqual(result, '')
        
        # Test with None
        form.cleaned_data = {'name': None}
        result = form.clean_name()
        self.assertIsNone(result)

    def test_clean_name_with_special_characters(self):
        """Test that clean_name handles special characters correctly via slug."""
        Department.objects.create(
            name="IT & Support",
            created_by=self.user
        )

        form_data = {
            'name': 'IT and Support',
            'description': 'Similar name'
        }
        form = CreateDepartmentForm(data=form_data)
        self.assertTrue(form.is_valid())

