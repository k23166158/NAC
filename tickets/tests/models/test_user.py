from django.test import TestCase
from django.db.utils import IntegrityError
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model

# Get the custom user model defined in settings
User = get_user_model()

class UserModelTests(TestCase):

    def setUp(self):
        """Set up a base user for testing."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            first_name='John',
            last_name='Doe',
            password='password123',
            bio='Just a test user.'
        )

    def test_create_user_successful(self):
        """Test that a user is created successfully with valid data."""
        self.assertIsInstance(self.user, User)
        self.assertEqual(self.user.email, 'test@example.com')
        self.assertEqual(self.user.first_name, 'John')
        self.assertEqual(self.user.last_name, 'Doe')
        self.assertEqual(self.user.bio, 'Just a test user.')
        self.assertTrue(self.user.check_password('password123'))

    def test_full_name_method(self):
        """Test the full_name method returns the correct string."""
        expected_full_name = 'John Doe'
        self.assertEqual(self.user.full_name(), expected_full_name)

    def test_email_unique_constraint(self):
        """Test that creating a user with a duplicate email raises an IntegrityError."""
        with self.assertRaises(IntegrityError):
            User.objects.create_user(
                username='testuser2',
                email='test@example.com',  # Duplicate email
                first_name='Jane',
                last_name='Doe',
                password='password123'
            )

    def test_required_fields(self):
        """
        Test that validation fails if required fields are blank.
        Note: We use full_clean() because standard save() does not validation 
        blank=False automatically without a ModelForm.
        """
        # Test missing email
        user_no_email = User(username='noemail', first_name='Test', last_name='User')
        with self.assertRaises(ValidationError):
            user_no_email.full_clean()

        # Test missing first_name
        user_no_first = User(username='nofirst', email='unique@example.com', last_name='User')
        with self.assertRaises(ValidationError):
            user_no_first.full_clean()
        
        # Test missing last_name
        user_no_last = User(username='nolast', email='unique2@example.com', first_name='Test')
        with self.assertRaises(ValidationError):
            user_no_last.full_clean()

    def test_meta_ordering(self):
        """Test that users are ordered by last_name then first_name."""
        # Create users in a random order
        User.objects.create_user(username='a', email='a@test.com', first_name='Alice', last_name='Baker')
        User.objects.create_user(username='b', email='b@test.com', first_name='Bob', last_name='Alpha')
        User.objects.create_user(username='c', email='c@test.com', first_name='Charlie', last_name='Baker')

        users = User.objects.all()
        
        # Expected Order:
        # 1. Alpha, Bob (Alpha comes before Baker)
        # 2. Baker, Alice (Alice comes before Charlie)
        # 3. Baker, Charlie
        # 4. Doe, John (Created in setUp, 'Doe' comes after 'Baker')

        self.assertEqual(users[0].last_name, 'Alpha')
        self.assertEqual(users[1].first_name, 'Alice')
        self.assertEqual(users[2].first_name, 'Charlie')
        self.assertEqual(users[3].last_name, 'Doe')

    def test_profile_picture_upload(self):
        """Test that profile picture field accepts None (since null=True)."""
        # We verify that we can explicitly set it to None without error
        self.user.profile_picture = None
        try:
            self.user.full_clean()
            self.user.save()
        except ValidationError:
            self.fail("User profile_picture cannot be null.")