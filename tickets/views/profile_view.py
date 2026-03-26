from django.contrib.auth.views import redirect_to_login
from django.shortcuts import get_object_or_404, render
from django.views import View
from tickets.models import User, Ticket, UserDepartments


class ProfileView(View):
    """Displays a user's profile by profile_slug."""
    def get(self, request, profile_slug):
        """Render profile page for the given profile_slug."""
        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path())

        profile_user = self._get_profile_user(profile_slug)
        context = self._base_context(request, profile_user)
        context.update(self._ticket_stats(profile_user))
        context.update(self._department_stats(profile_user))
        return render(request, "profile.html", context)

    def _get_profile_user(self, profile_slug):
        """Return the profile user for the given slug."""
        return get_object_or_404(User, profile_slug=profile_slug)

    def _base_context(self, request, profile_user):
        """Return base context shared by the profile view."""
        return {
            "profile_user": profile_user,
            "is_own_profile": request.user.pk == profile_user.pk,
        }

    def _ticket_stats(self, profile_user):
        """Return ticket statistics for the profile user."""
        stats = self._assigned_ticket_stats(profile_user)
        stats.update(self._created_ticket_stats(profile_user))
        return stats

    def _assigned_ticket_stats(self, profile_user):
        """Return stats for tickets where user is a participant."""
        assigned = Ticket.objects.filter(participants__user=profile_user)
        return {
            "assigned_active_count": assigned.filter(
                status__in=[Ticket.Status.OPEN]
            ).distinct().count(),
            "assigned_completed_count": assigned.filter(
                status=Ticket.Status.CLOSED
            ).distinct().count(),
        }

    def _created_ticket_stats(self, profile_user):
        """Return stats for tickets created by the user."""
        created = Ticket.objects.filter(created_by=profile_user)
        return {
            "created_total_count": created.count(),
            "created_closed_count": created.filter(
                status=Ticket.Status.CLOSED
            ).count(),
        }

    def _department_stats(self, profile_user):
        """Return department statistics for the profile user."""
        qs = UserDepartments.objects.select_related("department").filter(
            user=profile_user
        )
        departments = [ud.department for ud in qs]
        return {
            "department_count": qs.count(),
            "departments": departments,
        }
