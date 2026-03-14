from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.shortcuts import redirect
from django.views.generic import ListView

from tickets.models import Department, DepartmentInvitation

from tickets.models import Department, DepartmentInvitation, UserDepartments, Notification
from tickets.helpers.notifications import create_notification

class DepartmentManageView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    """View for managing departments. Only accessible to staff members."""

    template_name = "department_manage.html"
    context_object_name = "departments"
    paginate_by = 10
    login_url = "/login/"
    raise_exception = False

    def test_func(self):
        """Check if the user is a staff member."""
        return self.request.user.is_staff or self.request.user.is_superuser

    def get_queryset(self):
        """Return filtered, annotated departments for the current user."""
        return Department.assigned_to_user_with_ticket_counts(
            self.request.user,
            self.request.GET.get("q", ""),
        )

    def get_context_data(self, **kwargs):
        """Add invitation data to the rendered page context."""
        context = super().get_context_data(**kwargs)
        context["invitations"] = DepartmentInvitation.pending_for_user(self.request.user)
        return context

    def _notify_invite_sender(self, *, sender, actor, notification_type, department):
        """Notify the inviter about an invite outcome."""
        create_notification(
            user=sender,
            actor=actor,
            notification_type=notification_type,
            target_object=department,
        )

    def _add_user_to_department(self, request, department):
        """Persist department membership for the current user."""
        UserDepartments.objects.get_or_create(user=request.user, department=department)

    def _accept_invite(self, request, invite):
        """Accept a department invitation and add user to department."""
        invite.status = 'accepted'
        invite.save()
        self._add_user_to_department(request, invite.department)
        messages.success(
            request,
            f'You have joined the department "{invite.department.name}".',
        )
        self._notify_invite_sender(
            sender=invite.sender,
            actor=request.user,
            notification_type=Notification.NotificationType.DEPT_INVITE_ACCEPTED,
            department=invite.department,
        )

    def _decline_invite(self, request, invite):
        """Decline a department invitation."""
        invite.status = 'declined'
        invite.save()
        messages.info(
            request,
            f'You have declined the invitation to "{invite.department.name}".',
        )
        self._notify_invite_sender(
            sender=invite.sender,
            actor=request.user,
            notification_type=Notification.NotificationType.DEPT_INVITE_DECLINED,
            department=invite.department,
        )

    def _get_invite_and_action(self, request):
        """Return (invite, action, redirect_or_none). If redirect, caller should return it."""
        invite_id = request.POST.get('invite_id')
        action = request.POST.get('action')
        if not invite_id or not action:
            messages.error(request, 'Invalid request.')
            return None, None, redirect('department_manage')
        invite = get_object_or_404(
            DepartmentInvitation,
            pk=invite_id,
            recipient=request.user,
            status='pending',
        )
        return invite, action, None

    def post(self, request):
        """Handle POST requests: accept or decline department invitations."""
        level, text = DepartmentInvitation.process_action_for_user(
            user=request.user,
            invite_id=request.POST.get("invite_id"),
            action=request.POST.get("action"),
        )
        getattr(messages, level)(request, text)
        return redirect("department_manage")
