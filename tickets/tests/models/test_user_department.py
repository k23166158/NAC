from django.test import TestCase
from django.contrib.auth import get_user_model
from tickets.models import Department, UserDepartments

class UserDepartmentsModelTests(TestCase):
    """Tests for the UserDepartments model."""

    def test_str_representation(self):
        """Test the string representation of UserDepartments."""
        User = get_user_model()
        user = User.objects.create_user(
            username="alice", email="alice@example.com", password="pw"
        )
        dept = Department.objects.create(name="Engineering", created_by=user)
        
        assignment = UserDepartments.objects.create(user=user, department=dept)
        
        expected_str = f"Assignment: User alice -> Engineering"
        self.assertEqual(str(assignment), expected_str)