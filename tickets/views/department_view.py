from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import OuterRef, Subquery
from django.http import HttpResponseForbidden
from django.shortcuts import render, get_object_or_404, redirect
from django.views import View

from ..models import Department, Ticket, TicketMessage, UserDepartments, DepartmentInvitation

User = get_user_model()


class DepartmentView(LoginRequiredMixin, View):
    """View for displaying department details."""

    def get(self, request, department_slug):
        """Handle GET requests for the department view."""
        department = get_object_or_404(Department, slug=department_slug)

        if not self.is_member(request.user, department) and not request.user.is_superuser:
            return HttpResponseForbidden("You are not allowed to access this.")

        context = self.build_context(request, department)
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

    def _get_page(self, request, queryset, param, per_page=5):
        """Return a paginated page and its total count."""
        from django.core.paginator import Paginator
        paginator = Paginator(queryset, per_page)
        return paginator.get_page(request.GET.get(param, 1)), paginator.count

    def _get_staff_context(self, request, department):
        """Helper to fetch staff and invited users context."""
        current_staff = self.get_current_staff(department)
        pending = DepartmentInvitation.objects.filter(department=department, status='pending')
        invited_users = [invite.recipient for invite in pending.select_related('recipient')]
        staff_page, _ = self._get_page(request, list(current_staff) + invited_users, 'staff_page')
        return current_staff, invited_users, staff_page

    def build_context(self, request, department):
        """Build the context for rendering the department view, including multiple paginators."""
        c_staff, inv, s_page = self._get_staff_context(request, department)
        act_p, act_c = self._get_page(request, self.get_tickets(department, ['open', 'pending']), 'active_page')
        cls_p, cls_c = self._get_page(request, self.get_tickets(department, ['closed']), 'closed_page')
        return {
            "department": department, "staff_page": s_page, "invited_users": inv,
            "available_staff": self.get_available_staff(c_staff, inv),
            "active_tickets_page": act_p, "closed_tickets_page": cls_p,
            "active_tickets_count": act_c, "closed_tickets_count": cls_c,
        }

    def get_current_staff(self, department):
        """Get the current staff assigned to the department."""
        return [
            assignment.user
            for assignment in department.assigned_users.select_related('user').all()
        ]

    def get_available_staff(self, current_staff, invited_users):
        """Get staff users not currently assigned or invited to the department."""
        current_ids = [u.id for u in current_staff] + [u.id for u in invited_users]
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
            self.update_staff_assignment(request, user_id, department, action)

    def _send_department_invite(self, request, user, department):
        """Create or get pending invite and set success/info message."""
        invite, created = DepartmentInvitation.objects.get_or_create(
            department=department,
            recipient=user,
            status='pending',
            defaults={'sender': request.user},
        )
        name = user.get_full_name() or user.username
        if created:
            messages.success(request, f'Invitation sent to {name}.')
        else:
            messages.info(request, f'{name} was already invited.')

    def _invite_staff_to_department(self, request, user, department):
        """Send or note an existing invite for a staff user to the department."""
        if not user.is_staff:
            messages.error(request, 'Only staff users can be invited to a department.')
            return
        if UserDepartments.objects.filter(user=user, department=department).exists():
            name = user.get_full_name() or user.username
            messages.warning(request, f'{name} is already in this department.')
            return
        self._send_department_invite(request, user, department)

    def update_staff_assignment(self, request, user_id, department, action):
        """Add, remove, or invite a staff member for the department."""
        user = get_object_or_404(User, id=user_id)
        if action == 'add':
            self._invite_staff_to_department(request, user, department)
            return
        if action == 'remove':
            UserDepartments.objects.filter(user=user, department=department).delete()
            return
        if action == 'remove_invite':
            DepartmentInvitation.objects.filter(department=department, recipient=user, status='pending').delete()
            return
