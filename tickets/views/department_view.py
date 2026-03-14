from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponseForbidden
from django.shortcuts import redirect, render
from django.views import View

from ..models import Department, Ticket, TicketMessage, UserDepartments, DepartmentInvitation
from tickets.models.notification import Notification
from tickets.helpers.notifications import create_notification

User = get_user_model()


class DepartmentView(LoginRequiredMixin, View):
    """View for displaying department details."""

    def get(self, request, department_slug):
        """Handle GET requests for the department view."""
        department = Department.get_by_slug_or_404(department_slug)
        if not department.can_view(request.user):
            return HttpResponseForbidden("You are not allowed to access this.")
        return render(request, "department.html", department.build_view_context(request))

    def post(self, request, department_slug):
        """Handle POST requests to add or remove staff."""
        department = Department.get_by_slug_or_404(department_slug)
        if not department.can_manage_staff(request.user):
            return HttpResponseForbidden("You are not allowed to access this.")
        self._process_staff_action(request, department)
        return redirect("department", department_slug=department_slug)

    def _process_staff_action(self, request, department):
        """Run department staff action and publish any response message."""
        outcome = department.process_staff_change(
            actor=request.user,
            user_id=request.POST.get("user_id"),
            action=request.POST.get("action"),
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

    def _notify_invited_user(self, request, user, department):
        """Notify a staff user that they were invited to a department."""
        create_notification(
            user=user,
            actor=request.user,
            notification_type=Notification.NotificationType.DEPT_INVITED,
            target_object=department,
        )

    def _notify_removed_member(self, request, user, department):
        """Notify a staff user that they were removed from a department."""
        create_notification(
            user=user,
            actor=request.user,
            notification_type=Notification.NotificationType.DEPT_MEMBER_REMOVED,
            target_object=department,
        )

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
            self._notify_invited_user(request, user, department)
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
        actions = {
            "add": lambda: self._invite_staff_to_department(request, user, department),
            "remove": lambda: self._remove_staff_from_department(request, user, department),
            "remove_invite": lambda: DepartmentInvitation.objects.filter(
                department=department, recipient=user, status="pending"
            ).delete(),
        }
        handler = actions.get(action)
        if handler:
            handler()

    def _remove_staff_from_department(self, request, user, department):
        """Remove staff membership and notify the removed user."""
        if not UserDepartments.objects.filter(user=user, department=department).exists():
            return
        UserDepartments.objects.filter(user=user, department=department).delete()
        self._notify_removed_member(request, user, department)
