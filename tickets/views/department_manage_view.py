from django.db.models import Count, Q
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages

from tickets.models import Department, DepartmentInvitation, UserDepartments

class DepartmentManageView(LoginRequiredMixin, UserPassesTestMixin, View):
    """View for managing departments. Only accessible to staff members."""
    login_url = '/login/'
    raise_exception = False

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

    def get_departments_queryset(self, user):
        """Return departments the user is in, annotated with ticket counts."""
        return self._annotate_department_ticket_counts(self._base_departments_queryset(user))

    def get(self, request):
        """Handle GET requests for the department manage view."""
        departments = self.get_departments_queryset(request.user)
        invitations = DepartmentInvitation.objects.filter(
            recipient=request.user,
            status='pending'
        ).select_related('department', 'sender').order_by('-created_at')
        context = {'departments': departments, 'invitations': invitations}
        return render(request, "department_manage.html", context)

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

    def _decline_invite(self, request, invite):
        """Decline a department invitation."""
        invite.status = 'declined'
        invite.save()
        messages.info(
            request,
            f'You have declined the invitation to "{invite.department.name}".',
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

