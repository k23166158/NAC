import csv
from io import StringIO
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.shortcuts import render
from django.views import View
from django.db import transaction

User = get_user_model()

class BulkUserImportView(LoginRequiredMixin, UserPassesTestMixin, View):
    """View to handle bulk import of users via CSV upload."""
    
    template_name = 'user_bulk_import.html'
    required_fields = ['username', 'email', 'first_name', 'last_name', 'password']

    def test_func(self):
        """Check if user is staff or superuser."""
        return self.request.user.is_staff or self.request.user.is_superuser

    def get(self, request):
        """Render the upload form."""
        return render(request, self.template_name)

    def _validate_fields(self, row, row_number, failed_rows):
        """Validate required fields."""
        if not all(row.get(field) for field in self.required_fields):
            failed_rows.append({'row': row_number, 'details': str(row), 'error': 'Missing required fields'})
            return False
        return True

    def _check_email_conflict(self, username, email, row_number, failed_rows):
        """Check if the email is taken by another username."""
        existing_email_user = User.objects.filter(email=email).first()
        if existing_email_user and existing_email_user.username != username:
            failed_rows.append({'row': row_number, 'details': f"email: {email}", 'error': 'Email is already taken by another user'})
            return True
        return False

    def _update_user_fields(self, user, email, first_name, last_name, password):
        """Helper to assign fields to the user instance."""
        user.email = email
        user.first_name = first_name
        user.last_name = last_name
        user.set_password(password)
        user.save()

    @transaction.atomic
    def _save_user_transaction(self, row):
        """Save or update the user in a transaction."""
        username = row['username'].strip()
        email = row['email'].strip()
        first_name = row['first_name'].strip()
        last_name = row['last_name'].strip()
        password = row['password'].strip()

        user, created = User.objects.get_or_create(
            username=username,
            defaults={'email': email, 'first_name': first_name, 'last_name': last_name}
        )

        self._update_user_fields(user, email, first_name, last_name, password)

    def _create_or_update_user(self, row, row_number, failed_rows):
        """Create or update user from validated row."""
        username = row['username'].strip()
        email = row['email'].strip()

        if self._check_email_conflict(username, email, row_number, failed_rows):
            return False

        try:
            self._save_user_transaction(row)
            return True
        except Exception as e:
            failed_rows.append({'row': row_number, 'details': str(row), 'error': str(e)})
            return False

    def _process_user_row(self, row, row_number, failed_rows):
        """Process a single user row."""
        if not self._validate_fields(row, row_number, failed_rows):
            return False
        return self._create_or_update_user(row, row_number, failed_rows)

    def _read_csv(self, request, csv_file):
        """Read and decode CSV file."""
        try:
            file_data = csv_file.read().decode('utf-8')
            return csv.DictReader(StringIO(file_data)), None
        except Exception as e:
            return None, render(request, self.template_name, {'error': f'Error reading CSV file: {str(e)}'})

    def _validate_header(self, request, csv_reader):
        """Validate CSV header."""
        if csv_reader.fieldnames and not all(field in csv_reader.fieldnames for field in self.required_fields):
            return render(request, self.template_name, {
                'error': f'CSV must contain the following columns: {", ".join(self.required_fields)}'
            })
        return None

    def _process_single_row(self, row_data, failed_rows):
        """Process a single row entry from enumeration."""
        row_number, row = row_data
        if self._process_user_row(row, row_number, failed_rows):
            return 1
        return 0

    def _process_rows(self, csv_reader):
        """Process all CSV rows."""
        success_count = 0
        failed_rows = []
        rows = list(enumerate(csv_reader, start=2))
        for row_data in rows:
            success_count += self._process_single_row(row_data, failed_rows)
        return success_count, failed_rows

    def _render_success(self, request, success_count, failed_rows):
        """Render the success view with results."""
        context = {
            'success_count': success_count,
            'failed_rows': failed_rows,
            'total_processed': success_count + len(failed_rows)
        }
        return render(request, self.template_name, context)

    def _handle_csv_upload(self, request, csv_file):
        """Process the uploaded CSV file."""
        csv_reader, error_response = self._read_csv(request, csv_file)
        if error_response:
            return error_response

        error_response = self._validate_header(request, csv_reader)
        if error_response:
            return error_response

        success_count, failed_rows = self._process_rows(csv_reader)
        return self._render_success(request, success_count, failed_rows)

    def post(self, request):
        """Handle the uploaded CSV file."""
        csv_file = request.FILES.get('csv_file')
        
        if not csv_file:
            return render(request, self.template_name, {'error': 'Please upload a CSV file.'})
            
        if not csv_file.name.endswith('.csv'):
            return render(request, self.template_name, {'error': 'Please upload a valid CSV file.'})

        return self._handle_csv_upload(request, csv_file)
