import csv
from io import StringIO
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model

User = get_user_model()

class BulkUserExportViewTests(TestCase):
    """Tests for BulkUserExportViewTests."""
    def setUp(self):
        """Test for setUp."""
        self.client = Client()
        self.admin_user = User.objects.create_superuser('admin', 'admin@example.com', 'password')
        self.staff_user = User.objects.create_user('staff', 'staff@example.com', 'password', is_staff=True)
        self.regular_user = User.objects.create_user('regular', 'regular@example.com', 'password')
        self.url = reverse('bulk_user_export')

    def test_view_access_admin(self):
        """Test for test_view_access_admin."""
        self.client.login(username='admin', password='password')
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/csv')

    def test_view_access_staff(self):
        """Test for test_view_access_staff."""
        self.client.login(username='staff', password='password')
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_view_access_regular_user(self):
        """Test for test_view_access_regular_user."""
        self.client.login(username='regular', password='password')
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 403)

    def test_view_access_unauthenticated(self):
        """Test for test_view_access_unauthenticated."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)

    def test_csv_content(self):
        """Test for test_csv_content."""
        self.client.login(username='admin', password='password')
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

        content = response.content.decode('utf-8')
        csv_reader = csv.reader(StringIO(content))
        rows = list(csv_reader)

        # Check headers
        self.assertEqual(rows[0], ['username', 'email', 'first_name', 'last_name', 'password'])

        # Find our admin user in the export (there might be others like staff, regular)
        admin_row = None
        for row in rows[1:]:
            if row[0] == 'admin':
                admin_row = row
                break

        self.assertIsNotNone(admin_row)
        self.assertEqual(admin_row[1], 'admin@example.com')
        self.assertEqual(admin_row[4], '********')
