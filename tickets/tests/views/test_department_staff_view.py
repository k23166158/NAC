from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model

from tickets.models import Department, UserDepartments, DepartmentInvitation

User = get_user_model()


class DepartmentStaffViewTests(TestCase):
    """Tests for the DepartmentStaffView."""

    def setUp(self):
        self.owner = User.objects.create_user(username="o", email="o@e.com", password="p", is_staff=True)
        self.mem = User.objects.create_user(username="m", email="m@e.com", password="p")
        self.out = User.objects.create_user(username="out", email="out@e.com", password="p")
        self.dept = Department.objects.create(name="IT", created_by=self.owner)
        UserDepartments.objects.create(user=self.mem, department=self.dept)
        UserDepartments.objects.create(user=self.owner, department=self.dept)
        self.url = reverse("department_staff", kwargs={"department_slug": self.dept.slug})

    def test_non_member_gets_403(self):
        self.client.force_login(self.out)
        self.assertEqual(self.client.get(self.url).status_code, 403)

    def test_unauthenticated_redirects_to_login(self):
        res = self.client.get(self.url)
        self.assertEqual(res.status_code, 302)

    def test_member_sees_staff_list(self):
        self.client.force_login(self.mem)
        res = self.client.get(self.url)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.context["page"].paginator.count, 2)

    def test_invited_users_included(self):
        invited = User.objects.create_user(username="inv", email="inv@e.com", password="p", is_staff=True)
        DepartmentInvitation.objects.create(
            department=self.dept, recipient=invited, sender=self.owner, status="pending"
        )

        self.client.force_login(self.mem)
        res = self.client.get(self.url)
        self.assertEqual(res.context["page"].paginator.count, 3)
        self.assertIn(invited, res.context["invited_users"])
