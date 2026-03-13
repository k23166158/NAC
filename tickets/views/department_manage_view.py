from django.db.models import Count, Q
from django.views.generic import ListView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages

from tickets.models import Department, DepartmentInvitation, UserDepartments, Notification
from tickets.helpers.notifications import create_notification

class DepartmentManageView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    """View for managing departments. Only accessible to staff members."""
    login_url = '/login/'
    raise_exception = False
    template_name = "department_manage.html"
    context_object_name = "departments"
    paginate_by = 10

    def test_func(self):
        """Check if the user is a staff member."""
        return self.request.user.is_staff or self.request.user.is_superuser

    def _base_departments_queryset(self, user):
        """Return departments the user is in (filtered, distinct)."""
        return (
            Department.objects.filter(assigned_users__user=user)
            .select_related('created_by')
            .distinct()
        )

    def _annotate_department_ticket_counts(self, queryset):
        """Annotate department queryset with active and completed ticket counts."""
        return queryset.annotate(
            active_ticket_count=Count(
                'assigned_tickets',
                filter=Q(assigned_tickets__ticket__status__in=['open', 'pending']),
                distinct=True,
            ),
            completed_ticket_count=Count(
                'assigned_tickets',
                filter=Q(assigned_tickets__ticket__status='closed'),
                distinct=True,
            ),
        ).prefetch_related('assigned_users__user').order_by('name')

    def get_queryset(self):
        """Return departments the user is in, filtered by search query and annotated with ticket counts."""
        queryset = self._base_departments_queryset(self.request.user)
        search_query = self.request.GET.get('q')
        if search_query:
            queryset = queryset.filter(
                Q(name__icontains=search_query) |
                Q(description__icontains=search_query)
            )
        return self._annotate_department_ticket_counts(queryset)

    def get_context_data(self, **kwargs):
        """Add invitations to context."""
        context = super().get_context_data(**kwargs)
        context['invitations'] = DepartmentInvitation.objects.filter(
            recipient=self.request.user,
            status='pending'
        ).select_related('department', 'sender').order_by('-created_at')
        return context

    def _accept_invite(self, request, invite):
        """Accept a department invitation and add user to department."""
        invite.status = 'accepted'
        invite.save()
        UserDepartments.objects.get_or_create(
            user=request.user,
            department=invite.department,
        )
        messages.success(
            request,
            f'You have joined the department "{invite.department.name}".',
        )
        create_notification(
            user=invite.sender,
            actor=request.user,
            notification_type=Notification.NotificationType.DEPT_INVITE_ACCEPTED,
            target_object=invite.department,
        )

    def _decline_invite(self, request, invite):
        """Decline a department invitation."""
        invite.status = 'declined'
        invite.save()
        messages.info(
            request,
            f'You have declined the invitation to "{invite.department.name}".',
        )
        create_notification(
            user=invite.sender,
            actor=request.user,
            notification_type=Notification.NotificationType.DEPT_INVITE_DECLINED,
            target_object=invite.department,
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
        invite, action, resp = self._get_invite_and_action(request)
        if resp is not None:
            return resp
        if action == 'accept':
            self._accept_invite(request, invite)
            return redirect('department_manage')
        if action == 'decline':
            self._decline_invite(request, invite)
            return redirect('department_manage')
        messages.error(request, 'Invalid action.')
        return redirect('department_manage')

