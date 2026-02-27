from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib.messages import get_messages
from tickets.models import Department, UserDepartments, DepartmentInvitation, Ticket, TicketAssigned

User = get_user_model()

class DepartmentViewTests(TestCase):
    """Tests for the DepartmentView."""

    def setUp(self):
        """Set up users and a department for testing."""
        self.client = Client()
        self.owner = User.objects.create_user(
            username="owner", email="owner@example.com", password="pw", is_staff=True
        )
        self.member = User.objects.create_user(
            username="member", email="member@example.com", password="pw"
        )
        self.outsider = User.objects.create_user(
            username="outsider", email="outsider@example.com", password="pw"
        )

        self.department = Department.objects.create(name="IT", created_by=self.owner)
        
        UserDepartments.objects.create(user=self.member, department=self.department)
        UserDepartments.objects.create(user=self.owner, department=self.department)

        self.url = reverse('department', kwargs={'department_slug': self.department.slug})

    def test_get_forbidden_for_non_member(self):
        """Test that non-members cannot access the department view."""
        self.client.force_login(self.outsider)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 403)

    def test_superuser_can_access_non_member(self):
        """Test that a superuser can access the view even if not a member."""
        superuser = User.objects.create_superuser(
            username="super", email="super@example.com", password="pw"
        )
        self.client.force_login(superuser)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_get_success_for_member(self):
        """Test that members can access the department view."""
        self.client.force_login(self.member)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "department.html")
        self.assertIn("active_tickets", response.context)
        self.assertIn("available_staff", response.context)
        self.assertIn("invited_staff", response.context)

    def test_get_context_includes_active_and_closed_tickets(self):
        """Test that build_context includes active and closed tickets with annotations."""
        open_ticket = Ticket.objects.create(
            title="Open", created_by=self.member, status=Ticket.Status.OPEN
        )
        closed_ticket = Ticket.objects.create(
            title="Closed", created_by=self.member, status=Ticket.Status.CLOSED
        )
        TicketAssigned.objects.create(ticket=open_ticket, department=self.department)
        TicketAssigned.objects.create(ticket=closed_ticket, department=self.department)
        self.client.force_login(self.member)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["active_tickets"]), 1)
        self.assertEqual(len(response.context["closed_tickets"]), 1)
        self.assertIn("staff", response.context)
        self.assertIn("department", response.context)

    def test_post_add_staff_sends_invite(self):
        """Test that the owner adding staff actually sends an invite."""
        new_staff = User.objects.create_user(
            username="newstaff", email="newstaff@example.com", password="pw", is_staff=True
        )
        self.client.force_login(self.owner)
        
        response = self.client.post(
            self.url, 
            {'action': 'add', 'user_id': new_staff.id}
        )
        
        self.assertRedirects(response, self.url)
        self.assertTrue(
            DepartmentInvitation.objects.filter(recipient=new_staff, department=self.department, status='pending').exists()
        )
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any("Invitation sent to" in str(m) for m in messages))

    def test_post_remove_staff_success(self):
        """Test that the owner can remove staff."""
        UserDepartments.objects.create(user=self.outsider, department=self.department)
        
        self.client.force_login(self.owner)
        response = self.client.post(
            self.url, 
            {'action': 'remove', 'user_id': self.outsider.id}
        )
        
        self.assertRedirects(response, self.url)
        self.assertFalse(
            UserDepartments.objects.filter(user=self.outsider, department=self.department).exists()
        )

    def test_post_remove_invite_success(self):
        """Test that the owner can revoke a pending invite."""
        new_staff = User.objects.create_user(
            username="invited", email="inv@example.com", password="pw", is_staff=True
        )
        DepartmentInvitation.objects.create(
            department=self.department, recipient=new_staff, sender=self.owner, status='pending'
        )
        
        self.client.force_login(self.owner)
        response = self.client.post(
            self.url, 
            {'action': 'remove_invite', 'user_id': new_staff.id}
        )
        
        self.assertRedirects(response, self.url)
        self.assertFalse(
            DepartmentInvitation.objects.filter(recipient=new_staff, department=self.department, status='pending').exists()
        )

    def test_post_forbidden_for_non_owner(self):
        """Test that regular members cannot add/remove staff."""
        self.client.force_login(self.member)
        response = self.client.post(
            self.url, 
            {'action': 'add', 'user_id': self.outsider.id}
        )
        self.assertEqual(response.status_code, 403)

    def test_post_no_user_id_does_nothing(self):
        """Test that submitting without a user_id safely redirects."""
        self.client.force_login(self.owner)
        response = self.client.post(self.url, {'action': 'add'})
        self.assertRedirects(response, self.url)

    def test_post_staff_non_owner_forbidden(self):
        """Test that staff who didn't create department cannot manage."""
        staff_user = User.objects.create_user(
            username="staff_other", email="so@example.com", password="pw", is_staff=True
        )
        self.client.force_login(staff_user)
        response = self.client.post(
            self.url,
            {'action': 'add', 'user_id': self.outsider.id}
        )
        self.assertEqual(response.status_code, 403)

    def test_post_unknown_action_ignored(self):
        """Test that an unknown action does not change staff."""
        self.client.force_login(self.owner)
        response = self.client.post(
            self.url,
            {'action': 'unknown', 'user_id': self.outsider.id}
        )
        self.assertRedirects(response, self.url)
        self.assertFalse(
            UserDepartments.objects.filter(
                user=self.outsider, department=self.department
            ).exists()
        )

    def test_post_invite_already_in_department_shows_warning(self):
        """Test that inviting a staff user already in the department shows warning."""
        staff_in_dept = User.objects.create_user(
            username="staffindept",
            email="sid@example.com",
            password="pw",
            is_staff=True,
        )
        UserDepartments.objects.create(user=staff_in_dept, department=self.department)
        self.client.force_login(self.owner)
        response = self.client.post(
            self.url,
            {'action': 'add', 'user_id': staff_in_dept.id},
        )
        self.assertRedirects(response, self.url)
        self.assertFalse(
            DepartmentInvitation.objects.filter(
                recipient=staff_in_dept,
                department=self.department,
            ).exists()
        )
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any("is already in this department" in str(m) for m in messages))

    def test_post_invite_non_staff_shows_error(self):
        """Test that inviting a non-staff user shows error and does not create invite."""
        self.client.force_login(self.owner)
        response = self.client.post(
            self.url,
            {'action': 'add', 'user_id': self.outsider.id},
        )
        self.assertRedirects(response, self.url)
        self.assertFalse(
            DepartmentInvitation.objects.filter(
                recipient=self.outsider,
                department=self.department,
            ).exists()
        )
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any("Only staff users can be invited" in str(m) for m in messages))

    def test_post_invite_already_invited_shows_info(self):
        """Test that inviting again when pending invite exists does not duplicate."""
        staff = User.objects.create_user(
            username="staff2", email="s2@example.com", password="pw", is_staff=True
        )
        DepartmentInvitation.objects.create(
            sender=self.owner,
            recipient=staff,
            department=self.department,
            status="pending",
        )
        self.client.force_login(self.owner)
        response = self.client.post(
            self.url, {"action": "add", "user_id": staff.id}
        )
        self.assertRedirects(response, self.url)
        self.assertEqual(
            DepartmentInvitation.objects.filter(
                recipient=staff, department=self.department, status="pending"
            ).count(),
            1,
        )
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any("was already invited" in str(m) for m in messages))

    def test_get_available_staff_excludes_invited(self):
        """Test that available staff does not include users who are already invited."""
        invited_staff = User.objects.create_user(
            username="invstaff", email="inv@example.com", password="pw", is_staff=True
        )
        DepartmentInvitation.objects.create(
            sender=self.owner,
            recipient=invited_staff,
            department=self.department,
            status="pending",
        )
        self.client.force_login(self.owner)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        available_staff = response.context['available_staff']
        self.assertNotIn(invited_staff, available_staff)