from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

User = get_user_model()


class UserModelTests(TestCase):
    def setUp(self):
        """Create a valid user for reuse in tests."""
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            first_name="Test",
            last_name="User",
            password="strong-password-123"
        )

    def test_user_is_created_correctly(self):
        """User should be created with required fields."""
        self.assertEqual(self.user.email, "test@example.com")
        self.assertEqual(self.user.first_name, "Test")
        self.assertEqual(self.user.last_name, "User")
        self.assertTrue(self.user.check_password("strong-password-123"))

    def test_email_is_unique(self):
        """Email field should be unique."""
        with self.assertRaises(Exception):
            User.objects.create_user(
                username="anotheruser",
                email="test@example.com",  # duplicate email
                first_name="Another",
                last_name="User",
                password="password123"
            )

    def test_first_name_is_required(self):
        """first_name should not allow blank values."""
        user = User(
            username="nofirstname",
            email="nofirst@example.com",
            first_name="",
            last_name="User"
        )
        with self.assertRaises(ValidationError):
            user.full_clean()

    def test_last_name_is_required(self):
        """last_name should not allow blank values."""
        user = User(
            username="nolastname",
            email="nolast@example.com",
            first_name="Test",
            last_name=""
        )
        with self.assertRaises(ValidationError):
            user.full_clean()

    def test_full_name_method(self):
        """full_name should return 'first_name last_name'."""
        self.assertEqual(self.user.full_name(), "Test User")

    def test_ordering_by_last_name_then_first_name(self):
        """Users should be ordered by last_name, then first_name."""
        User.objects.create_user(
            username="user2",
            email="user2@example.com",
            first_name="Alice",
            last_name="Brown",
            password="password123"
        )
        User.objects.create_user(
            username="user3",
            email="user3@example.com",
            first_name="Bob",
            last_name="Brown",
            password="password123"
        )

        users = list(User.objects.all())
        self.assertEqual(users[0].last_name, "Brown")
        self.assertEqual(users[0].first_name, "Alice")
        self.assertEqual(users[1].first_name, "Bob")
