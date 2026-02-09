from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile

User = get_user_model()

class BulkUserImportViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin_user = User.objects.create_superuser('admin', 'admin@example.com', 'password')
        self.staff_user = User.objects.create_user('staff', 'staff@example.com', 'password', is_staff=True)
        self.regular_user = User.objects.create_user('regular', 'regular@example.com', 'password')
        self.url = reverse('bulk_user_import')

    def test_view_access_admin(self):
        self.client.login(username='admin', password='password')
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_view_access_staff(self):
        self.client.login(username='staff', password='password')
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_view_access_regular_user(self):
        self.client.login(username='regular', password='password')
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 403)

    def test_view_access_unauthenticated(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)

    def test_post_no_file(self):
        self.client.login(username='admin', password='password')
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Please upload a CSV file.')

    def test_post_invalid_file_type(self):
        self.client.login(username='admin', password='password')
        invalid_file = SimpleUploadedFile("file.txt", b"file_content")
        response = self.client.post(self.url, {'csv_file': invalid_file})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Please upload a valid CSV file.')

    def test_post_invalid_csv_data(self):
        self.client.login(username='admin', password='password')
        invalid_csv = SimpleUploadedFile("file.csv", b"invalid_content\x80")
        response = self.client.post(self.url, {'csv_file': invalid_csv})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Error reading CSV file')

    def test_post_missing_headers(self):
        self.client.login(username='admin', password='password')
        csv_data = "username,email\nuser1,user1@example.com"
        csv_file = SimpleUploadedFile("file.csv", csv_data.encode('utf-8'))
        response = self.client.post(self.url, {'csv_file': csv_file})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'CSV must contain the following columns')

    def test_post_successful_import(self):
        self.client.login(username='admin', password='password')
        csv_data = "username,email,first_name,last_name,password\nnewuser,newuser@example.com,New,User,pass123"
        csv_file = SimpleUploadedFile("file.csv", csv_data.encode('utf-8'))
        response = self.client.post(self.url, {'csv_file': csv_file})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Successfully imported 1 user(s)')
        self.assertTrue(User.objects.filter(username='newuser').exists())

    def test_post_update_existing_user(self):
        self.client.login(username='admin', password='password')
        User.objects.create_user('existinguser', 'old@example.com', 'oldpass')
        csv_data = "username,email,first_name,last_name,password\nexistinguser,new@example.com,New,Name,newpass"
        csv_file = SimpleUploadedFile("file.csv", csv_data.encode('utf-8'))
        response = self.client.post(self.url, {'csv_file': csv_file})
        self.assertEqual(response.status_code, 200)
        
        user = User.objects.get(username='existinguser')
        self.assertEqual(user.email, 'new@example.com')
        self.assertEqual(user.first_name, 'New')

    def test_post_missing_fields_in_row(self):
        self.client.login(username='admin', password='password')
        csv_data = "username,email,first_name,last_name,password\nnewuser,,New,User,pass123"
        csv_file = SimpleUploadedFile("file.csv", csv_data.encode('utf-8'))
        response = self.client.post(self.url, {'csv_file': csv_file})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Failed Imports (1)')
        self.assertContains(response, 'Missing required fields')

    def test_post_email_conflict(self):
        self.client.login(username='admin', password='password')
        User.objects.create_user('otheruser', 'conflict@example.com', 'pass')
        csv_data = "username,email,first_name,last_name,password\nnewuser,conflict@example.com,New,User,pass123"
        csv_file = SimpleUploadedFile("file.csv", csv_data.encode('utf-8'))
        response = self.client.post(self.url, {'csv_file': csv_file})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Failed Imports (1)')
        self.assertContains(response, 'Email is already taken by another user')


    from unittest.mock import patch
    @patch('tickets.views.user_import_view.BulkUserImportView._save_user_transaction')
    def test_post_database_error(self, mock_save):
        mock_save.side_effect = Exception("Simulated DB Error")
        self.client.login(username='admin', password='password')
        csv_data = "username,email,first_name,last_name,password\nerruser,err@example.com,Err,User,pass123"
        csv_file = SimpleUploadedFile("file.csv", csv_data.encode('utf-8'))
        response = self.client.post(self.url, {'csv_file': csv_file})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Failed Imports (1)')
        self.assertContains(response, 'Simulated DB Error')



