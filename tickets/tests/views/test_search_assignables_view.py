from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model

from tickets.models import Department

User = get_user_model()


class SearchAssignablesViewTests(TestCase):
    """Tests for the search_assignables view which allows searching for staff users and departments to assign to tickets."""
    def setUp(self):
        """Set up test data including users and departments for testing the search assignables view."""
        self.url = reverse("search_assignables")

        self.creator = User.objects.create_user(username="creator",email="creator@example.com",password="password123",is_staff=True)

        self.staff_user = User.objects.create_user(username="staff1",email="staff1@example.com",password="password123",is_staff=True,first_name="Staff",last_name="User")

        self.other_staff = User.objects.create_user(username="helpdesk",email="helpdesk@example.com",password="password123",is_staff=True,first_name="Help",last_name="Desk")

        self.non_staff = User.objects.create_user(username="customer",email="customer@example.com",password="password123",is_staff=False)

        self.department = Department.objects.create(
            name="IT Support",
            created_by=self.creator,
        )

        self.other_department = Department.objects.create(
            name="Billing",
            created_by=self.creator,
        )

    def test_login_required(self):
        """Test that the search_assignables view requires login and redirects unauthenticated users."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)

    def test_search_returns_staff_and_departments(self):
        """Test that searching with a query returns matching staff users and departments in the expected format."""
        self.client.login(username="creator", password="password123")

        response = self.client.get(self.url, {"q": "it"})
        self.assertEqual(response.status_code, 200)

        data = response.json()

        self.assertIn(
            {
                "id": self.department.id,
                "type": "department",
                "label": "IT Support (Department)",
            },
            data,
        )

    def test_search_returns_only_staff_users(self):
        """Test that searching for staff users returns only those users and excludes non-staff users."""
        self.client.login(username="creator", password="password123")

        response = self.client.get(self.url, {"q": "staff"})
        data = response.json()

        self.assertTrue(
            any(
                r["type"] == "staff" and r["id"] == self.staff_user.id
                for r in data
            )
        )

        self.assertFalse(
            any(r["id"] == self.non_staff.id for r in data)
        )

    def test_staff_label_formatting(self):
        """Test that the label for staff users in the search results is formatted correctly with full name and username."""
        self.client.login(username="creator", password="password123")

        response = self.client.get(self.url, {"q": "staff"})
        data = response.json()

        self.assertIn(
            {
                "id": self.staff_user.id,
                "type": "staff",
                "label": "Staff User (@staff1)",
            },
            data,
        )

    def test_department_label_formatting(self):
        """Test that the label for departments in the search results is formatted correctly with the department name."""
        self.client.login(username="creator", password="password123")

        response = self.client.get(self.url, {"q": "bill"})
        data = response.json()

        self.assertEqual(
            data,
            [
                {
                    "id": self.other_department.id,
                    "type": "department",
                    "label": "Billing (Department)",
                }
            ],
        )

    def test_empty_query_returns_results(self):
        """Test that an empty search query returns a list of staff users and departments, ensuring the endpoint can handle empty queries gracefully."""
        self.client.login(username="creator", password="password123")

        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertGreater(len(data), 0)
