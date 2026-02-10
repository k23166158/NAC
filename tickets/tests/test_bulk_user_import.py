from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, Client
from django.urls import reverse

User = get_user_model()


class BulkUserImportViewTests(TestCase):
    """Tests for BulkUserImportViewTests."""

    def setUp(self):
        """Test for setUp."""
        self.client = Client()
        self.admin_user = User.objects.create_superuser('admin', 'admin@example.com', 'password')
        self.staff_user = User.objects.create_user('staff', 'staff@example.com', 'password', is_staff=True)
        self.regular_user = User.objects.create_user('regular', 'regular@example.com', 'password')
        self.url = reverse('bulk_user_import')

    def test_view_access_admin(self):
        """Test for test_view_access_admin."""
        self.client.login(username='admin', password='password')
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

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

    def test_post_no_file(self):
        """Test for test_post_no_file."""
        self.client.login(username='admin', password='password')
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Please upload a CSV file.')

    def test_post_invalid_file_type(self):
        """Test for test_post_invalid_file_type."""
        self.client.login(username='admin', password='password')
        invalid_file = SimpleUploadedFile("file.txt", b"file_content")
        response = self.client.post(self.url, {'csv_file': invalid_file})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Please upload a valid CSV file.')

    def test_post_invalid_csv_data(self):
        """Test for test_post_invalid_csv_data."""
        self.client.login(username='admin', password='password')
        invalid_csv = SimpleUploadedFile("file.csv", b"invalid_content\x80")
        response = self.client.post(self.url, {'csv_file': invalid_csv})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Error reading CSV file')

    def test_post_missing_headers(self):
        """Test for test_post_missing_headers."""
        self.client.login(username='admin', password='password')
        csv_data = "username,email\nuser1,user1@example.com"
        csv_file = SimpleUploadedFile("file.csv", csv_data.encode('utf-8'))
        response = self.client.post(self.url, {'csv_file': csv_file})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'CSV must contain columns: ')

    def test_post_successful_import(self):
        """Test for test_post_successful_import."""
        self.client.login(username='admin', password='password')
        csv_data = "username,email,first_name,last_name,password,is_staff,is_superuser,is_active\nnewuser,newuser@example.com,New,User,pass123,False,False,True"
        csv_file = SimpleUploadedFile("file.csv", csv_data.encode('utf-8'))
        response = self.client.post(self.url, {'csv_file': csv_file})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Successfully imported 1 user(s)')
        self.assertTrue(User.objects.filter(username='newuser').exists())

    def test_post_update_existing_user(self):
        """Test for test_post_update_existing_user."""
        self.client.login(username='admin', password='password')
        User.objects.create_user('existinguser', 'old@example.com', 'oldpass')
        csv_data = "username,email,first_name,last_name,password,is_staff,is_superuser,is_active\nexistinguser,new@example.com,New,Name,newpass,False,False,True"
        csv_file = SimpleUploadedFile("file.csv", csv_data.encode('utf-8'))
        response = self.client.post(self.url, {'csv_file': csv_file})
        self.assertEqual(response.status_code, 200)

        user = User.objects.get(username='existinguser')
        self.assertEqual(user.email, 'new@example.com')
        self.assertEqual(user.first_name, 'New')

    def test_post_missing_fields_in_row(self):
        """Test for test_post_missing_fields_in_row."""
        self.client.login(username='admin', password='password')
        csv_data = "username,email,first_name,last_name,password,is_staff,is_superuser,is_active\nnewuser,,New,User,pass123,False,False,True"
        csv_file = SimpleUploadedFile("file.csv", csv_data.encode('utf-8'))
        response = self.client.post(self.url, {'csv_file': csv_file})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Failed Imports (1)')
        self.assertContains(response, 'Missing required fields')

    def test_post_email_conflict(self):
        """Test for test_post_email_conflict."""
        self.client.login(username='admin', password='password')
        User.objects.create_user('otheruser', 'conflict@example.com', 'pass')
        csv_data = "username,email,first_name,last_name,password,is_staff,is_superuser,is_active\nnewuser,conflict@example.com,New,User,pass123,False,False,True"
        csv_file = SimpleUploadedFile("file.csv", csv_data.encode('utf-8'))
        response = self.client.post(self.url, {'csv_file': csv_file})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Failed Imports (1)')
        self.assertContains(response, 'Email is already taken by another user')

    def test_boolean_parsing(self):
        """Test boolean string parsing edge cases."""
        self.client.login(username='admin', password='password')
        csv_data = "username,email,first_name,last_name,password,is_staff,is_superuser,is_active\ntestbool,bool@example.com,B,B,pass,true,FALSE,y"
        csv_file = SimpleUploadedFile("file.csv", csv_data.encode('utf-8'))
        response = self.client.post(self.url, {'csv_file': csv_file})
        self.assertEqual(response.status_code, 200)
        user = User.objects.get(username='testbool')
        self.assertTrue(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertTrue(user.is_active)

    from unittest.mock import patch
    @patch('tickets.views.user_import_view.BulkUserImportView._try_process_row')
    def test_post_process_row_exception(self, mock_try_process):
        """Test process row exception."""
        mock_try_process.side_effect = Exception("Row processing exception")
        self.client.login(username='admin', password='password')
        csv_data = "username,email,first_name,last_name,password,is_staff,is_superuser,is_active\nerruser,err@example.com,Err,User,pass123,False,False,True"
        csv_file = SimpleUploadedFile("file.csv", csv_data.encode('utf-8'))
        response = self.client.post(self.url, {'csv_file': csv_file})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Failed Imports (1)')
        self.assertContains(response, 'Row processing exception')

    from unittest.mock import patch
    @patch('tickets.views.user_import_view.BulkUserImportView._save_user_transaction')
    def test_post_database_error(self, mock_save):
        """Test for test_post_database_error."""
        mock_save.side_effect = Exception("Simulated DB Error")
        self.client.login(username='admin', password='password')
        csv_data = "username,email,first_name,last_name,password,is_staff,is_superuser,is_active\nerruser,err@example.com,Err,User,pass123,False,False,True"
        csv_file = SimpleUploadedFile("file.csv", csv_data.encode('utf-8'))
        response = self.client.post(self.url, {'csv_file': csv_file})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Failed Imports (1)')
        self.assertContains(response, 'Simulated DB Error')
