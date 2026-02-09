from django.db.models import Count, Q
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages

from ..models import Department, DepartmentInvitation, UserDepartments


class DepartmentManageView(LoginRequiredMixin, UserPassesTestMixin, View):
    """View for managing departments. Only accessible to staff members."""
    login_url = '/login/'
    raise_exception = False

    def test_func(self):
        """Check if the user is a staff member."""
        return self.request.user.is_staff

    def get(self, request):
        """Handle GET requests for the department manage view."""
        departments = (
            Department.objects.filter(assigned_users__user=request.user)
            .distinct()
            .annotate(
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
            )
            .prefetch_related('assigned_users__user')
            .order_by('name')
        )

        invitations = DepartmentInvitation.objects.filter(
            recipient=request.user,
            status='pending'
        ).select_related('department', 'sender').order_by('-created_at')

        context = {
            'departments': departments,
            'invitations': invitations,
        }
        return render(request, "department_manage.html", context)

    def post(self, request):
        """Handle POST requests: accept or decline department invitations."""
        invite_id = request.POST.get('invite_id')
        action = request.POST.get('action')

        if not invite_id or not action:
            messages.error(request, 'Invalid request.')
            return redirect('department_manage')

        invite = get_object_or_404(
            DepartmentInvitation,
            pk=invite_id,
            recipient=request.user,
            status='pending',
        )

        if action == 'accept':
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
        elif action == 'decline':
            invite.status = 'declined'
            invite.save()
            messages.info(
                request,
                f'You have declined the invitation to "{invite.department.name}".',
            )
        else:
            messages.error(request, 'Invalid action.')

        return redirect('department_manage')

