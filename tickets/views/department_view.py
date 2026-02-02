from django.shortcuts import render, get_object_or_404, redirect
from django.views import View
from django.db.models import OuterRef, Subquery
from django.contrib.auth import get_user_model
from ..models import Department, Ticket, TicketMessage, UserDepartments
from django.http import HttpResponseForbidden
from django.contrib.auth.mixins import LoginRequiredMixin

User = get_user_model()


class DepartmentView(LoginRequiredMixin, View):
    """View for displaying department details."""

    def get(self, request, department_slug):
        """Handle GET requests for the department view."""
        department = get_object_or_404(Department, slug=department_slug)

        if not self.is_member(request.user, department):
            return HttpResponseForbidden("You are not allowed to access this.")

        context = self.build_context(department)
        return render(request, "department.html", context)

    def post(self, request, department_slug):
        """Handle POST requests to add or remove staff."""
        department = get_object_or_404(Department, slug=department_slug)

        if not self.can_manage_staff(request.user, department):
            return HttpResponseForbidden("You are not allowed to access this.")

        self.process_staff_change(request, department)
        return redirect('department', department_slug=department_slug)

    def is_member(self, user, department):
        """Check if the user is a member of the department."""
        return UserDepartments.objects.filter(user=user, department=department).exists()

    def can_manage_staff(self, user, department):
        """Check if the user can manage staff for the department."""
        return user.is_staff and department.created_by == user

    def build_context(self, department):
        """Build the context for rendering the department view."""
        current_staff = self.get_current_staff(department)
        return {
            "department": department,
            "staff": current_staff,
            "available_staff": self.get_available_staff(current_staff),
            "active_tickets": self.get_tickets(department, ['open', 'pending']),
            "closed_tickets": self.get_tickets(department, ['closed']),
        }

    def get_current_staff(self, department):
        """Get the current staff assigned to the department."""
        return [
            assignment.user
            for assignment in department.assigned_users.select_related('user').all()
        ]

    def get_available_staff(self, current_staff):
        """Get staff users not currently assigned to the department."""
        current_ids = [u.id for u in current_staff]
        return User.objects.filter(is_staff=True).exclude(id__in=current_ids)

    def get_tickets(self, department, status_list):
        """Get tickets for the department with specified statuses."""
        qs = Ticket.objects.filter(
            assignments__department=department, status__in=status_list
        )
        return self.annotate_tickets(qs).order_by("-updated_at")

    def annotate_tickets(self, queryset):
        """Annotate tickets with their latest message details."""
        last_msg = TicketMessage.objects.filter(
            ticket_id=OuterRef("pk")
        ).order_by("-edited_at")
        
        return queryset.annotate(
            last_message_at=Subquery(last_msg.values("edited_at")[:1]),
            last_message_body=Subquery(last_msg.values("body")[:1]),
            last_message_sender_id=Subquery(last_msg.values("sender_id")[:1]),
            last_sender_is_staff=Subquery(last_msg.values("sender__is_staff")[:1]),
            last_sender_first=Subquery(last_msg.values("sender__first_name")[:1]),
            last_sender_last=Subquery(last_msg.values("sender__last_name")[:1]),
        )

    def process_staff_change(self, request, department):
        """Process adding or removing staff based on POST data."""
        user_id = request.POST.get('user_id')
        action = request.POST.get('action')

        if user_id:
            self.update_staff_assignment(user_id, department, action)

    def update_staff_assignment(self, user_id, department, action):
        """Add or remove a staff member from the department."""
        user = get_object_or_404(User, id=user_id)
        
        if action == 'add':
            UserDepartments.objects.get_or_create(user=user, department=department)
            return
        
        if action == 'remove':
            UserDepartments.objects.filter(user=user, department=department).delete()
