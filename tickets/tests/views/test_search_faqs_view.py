from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model

from tickets.models import Department, DepartmentFAQ

User = get_user_model()


def _create_user():
    """Create a test user for FAQ search tests."""
    return User.objects.create_user(
        username="testuser", email="test@example.com", password="password123",
    )


def _create_departments(user):
    """Create IT and HR departments for testing."""
    it = Department.objects.create(name="IT Support", created_by=user)
    hr = Department.objects.create(name="Human Resources", created_by=user)
    return it, hr


def _create_faqs(user, dept_it, dept_hr):
    """Create sample FAQs across departments for testing."""
    password = DepartmentFAQ.objects.create(
        department=dept_it, question="How do I reset my password?",
        answer="Go to the portal and click forgot password.", created_by=user,
    )
    vpn = DepartmentFAQ.objects.create(
        department=dept_it, question="How do I connect to the VPN?",
        answer="Download the VPN client and enter your credentials.", created_by=user,
    )
    leave = DepartmentFAQ.objects.create(
        department=dept_hr, question="How do I apply for annual leave?",
        answer="Submit a leave request through the HR portal.", created_by=user,
    )
    return password, vpn, leave


class SearchFaqsViewTests(TestCase):
    """Tests for the search_faqs view which searches department FAQs by keyword."""

    def setUp(self):
        """Set up test data including users, departments, and FAQs."""
        self.url = reverse("search_faqs")
        self.user = _create_user()
        self.dept_it, self.dept_hr = _create_departments(self.user)
        self.faq_password, self.faq_vpn, self.faq_leave = _create_faqs(
            self.user, self.dept_it, self.dept_hr
        )

    def test_login_required(self):
        """Test that unauthenticated users are redirected."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)

    def test_empty_query_returns_empty(self):
        """Test that an empty query returns no results."""
        self.client.login(username="testuser", password="password123")
        response = self.client.get(self.url, {"q": ""})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])

    def test_stop_words_only_returns_empty(self):
        """Test that a query with only stop words returns no results."""
        self.client.login(username="testuser", password="password123")
        response = self.client.get(self.url, {"q": "how do I"})
        self.assertEqual(response.json(), [])

    def test_short_words_only_returns_empty(self):
        """Test that a query with only short words returns no results."""
        self.client.login(username="testuser", password="password123")
        response = self.client.get(self.url, {"q": "ab cd"})
        self.assertEqual(response.json(), [])

    def test_keyword_matches_question(self):
        """Test that keywords matching FAQ questions return results."""
        self.client.login(username="testuser", password="password123")
        response = self.client.get(self.url, {"q": "reset password"})
        data = response.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["id"], self.faq_password.id)

    def test_keyword_matches_answer(self):
        """Test that keywords matching FAQ answers return results."""
        self.client.login(username="testuser", password="password123")
        response = self.client.get(self.url, {"q": "VPN client"})
        data = response.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["id"], self.faq_vpn.id)

    def test_result_format(self):
        """Test that results contain the expected fields."""
        self.client.login(username="testuser", password="password123")
        response = self.client.get(self.url, {"q": "password"})
        data = response.json()
        self.assertEqual(len(data), 1)
        result = data[0]
        self.assertIn("id", result)
        self.assertIn("question", result)
        self.assertIn("answer", result)
        self.assertIn("department", result)
        self.assertEqual(result["department"], "IT Support")

    def test_filter_by_department(self):
        """Test that results can be filtered by department IDs."""
        self.client.login(username="testuser", password="password123")
        response = self.client.get(self.url, {
            "q": "portal",
            "departments": [self.dept_hr.id],
        })
        data = response.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["department"], "Human Resources")

    def test_no_department_filter_searches_all(self):
        """Test that omitting departments searches across all FAQs."""
        self.client.login(username="testuser", password="password123")
        response = self.client.get(self.url, {"q": "portal"})
        data = response.json()
        self.assertEqual(len(data), 2)

    def test_case_insensitive_matching(self):
        """Test that keyword matching is case insensitive."""
        self.client.login(username="testuser", password="password123")
        response = self.client.get(self.url, {"q": "PASSWORD"})
        data = response.json()
        self.assertTrue(len(data) >= 1)

    def test_max_five_results(self):
        """Test that at most 5 results are returned."""
        self.client.login(username="testuser", password="password123")
        for i in range(10):
            DepartmentFAQ.objects.create(
                department=self.dept_it,
                question=f"Server issue number {i}",
                answer="Restart the server.",
                created_by=self.user,
            )
        response = self.client.get(self.url, {"q": "server"})
        data = response.json()
        self.assertLessEqual(len(data), 5)
