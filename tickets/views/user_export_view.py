import csv

from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.http import HttpResponse
from django.views import View

User = get_user_model()


class BulkUserExportView(LoginRequiredMixin, UserPassesTestMixin, View):
    """View to export all users to a CSV file."""

    def test_func(self):
        """Check if user is staff or superuser."""
        return self.request.user.is_staff or self.request.user.is_superuser

    def _write_users(self, writer):
        """Write user data rows to the CSV."""
        users = User.objects.all().order_by('id')
        for user in users:
            writer.writerow([
                user.username,
                user.email,
                user.first_name,
                user.last_name,
                '********',
                user.is_staff,
                user.is_superuser,
                user.is_active
            ])

    def get(self, request):
        """Handle the CSV export."""
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="users_export.csv"'

        writer = csv.writer(response)
        writer.writerow([
            'username', 'email', 'first_name', 'last_name', 'password',
            'is_staff', 'is_superuser', 'is_active'
        ])

        self._write_users(writer)

        return response
