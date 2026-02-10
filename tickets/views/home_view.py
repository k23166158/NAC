from datetime import timedelta

from django.db.models import OuterRef, Subquery, Q
from django.shortcuts import render
from django.utils import timezone
from django.views import View

from tickets.models import Ticket, TicketMessage, Department

class HomeView(View):
    """View for the home page/dashboard."""

    def get(self, request):
        """Handle GET request for home page."""
        if not request.user.is_authenticated: return render(request, "unauthenticated_home.html")
        scope = request.GET.get("scope", "personal")
        if scope not in {"personal", "department"}: scope = "personal"
        if scope == "department" and not request.user.is_staff: scope = "personal"
        qs = self._annotated_tickets(request.user, scope=scope)
        overdue = self._overdue_tickets(qs)
        context = {
            "scope": scope,
            "completed_tickets": self._completed_tickets(qs),
            "overdue_tickets": overdue,
            "active_tickets": self._active_tickets(qs, overdue),
        }
        return render(request, "home_view.html", context)

    def _base_tickets(self, user, scope="personal"):
        """Tickets visible to this user."""
        if scope == "department" and user.is_staff:
            return Ticket.objects.all()
        if not user.is_staff:
            return Ticket.objects.filter(created_by=user)
        dept_ids = Department.objects.filter(
            assigned_users__user=user
        ).values_list("id", flat=True)
        return Ticket.objects.filter(
            Q(created_by=user)
            | Q(messages__sender=user)
            | Q(participants__user=user)
            | Q(assignments__department_id__in=dept_ids)
        ).distinct()

    def _annotated_tickets(self, user, scope="personal"):
        """Tickets with last message info annotated."""
        last_msg = TicketMessage.objects.filter(ticket_id=OuterRef("pk")).order_by("-edited_at")
        return (
            self._base_tickets(user, scope=scope)
            .annotate(
                last_message_at=Subquery(last_msg.values("edited_at")[:1]),
                last_message_body=Subquery(last_msg.values("body")[:1]),
                last_message_sender_id=Subquery(last_msg.values("sender_id")[:1]),
                last_sender_is_staff=Subquery(last_msg.values("sender__is_staff")[:1]),
                last_sender_first=Subquery(last_msg.values("sender__first_name")[:1]),
                last_sender_last=Subquery(last_msg.values("sender__last_name")[:1]),
            )
        )

    def _completed_tickets(self, qs):
        """Tickets that are completed/closed."""
        return qs.filter(status=Ticket.Status.CLOSED).order_by("-updated_at")

    def _overdue_tickets(self, qs):
        """Tickets that are overdue for a response."""
        cutoff = timezone.now() - timedelta(days=7)
        return qs.filter(
            status__in=[Ticket.Status.OPEN, Ticket.Status.PENDING],
            last_message_at__isnull=False,
            last_message_at__lt=cutoff,
            last_sender_is_staff=False,
        ).order_by("-last_message_at")

    def _active_tickets(self, qs, overdue):
        """Tickets that are active and not overdue."""
        return qs.filter(
            status__in=[Ticket.Status.OPEN, Ticket.Status.PENDING],
        ).exclude(
            id__in=overdue.values_list("id", flat=True)
        ).order_by("-updated_at")