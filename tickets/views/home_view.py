from datetime import timedelta

from django.db.models import OuterRef, Subquery, Q
from django.shortcuts import render
from django.utils import timezone
from django.views import View

from tickets.models import Ticket, TicketMessage, Department, TicketAssigned, UserDepartments, TicketParticipant, User
from django.db.models import Exists, OuterRef

class HomeView(View):
    """View for the home page/dashboard."""

    def get(self, request):
        """Handle GET request for home page."""
        if not request.user.is_authenticated: 
            return render(request, "unauthenticated_home.html")
    
        scope = request.GET.get("scope", "personal")
        qs, scope = self.handle_scope(request.user, scope)
        overdue = self.overdue_tickets(qs)
        context = {
            "scope": scope,
            "completed_tickets": self.completed_tickets(qs),
            "overdue_tickets": overdue,
            "active_tickets": self.active_tickets(qs, overdue),
            "total_tickets": Ticket.objects.count() if self.is_admin(request.user) else None,
            "tickets_by_status": self.tickets_by_status() if self.is_admin(request.user) else None,
            "total_users": User.objects.count() if self.is_admin(request.user) else None,
        }
        return render(request, "home_view.html", context)

    def is_admin(self, user):
        return user.is_superuser or user.is_staff

    def tickets_by_status(self):
        """Returns a count of tickets by status."""
        return {
            "open": Ticket.objects.filter(status=Ticket.Status.OPEN).count(),
            "pending": Ticket.objects.filter(status=Ticket.Status.PENDING).count(),
            "closed": Ticket.objects.filter(status=Ticket.Status.CLOSED).count(),
        }

    def handle_scope(self, user, scope):
        """Handles the tickets to display depending on the scope selected by the user"""
        if not user.is_staff:
            return self.annotated_tickets(user, scope="personal"), "personal"

        if scope not in ("personal", "department", "assigned"):
            scope = "personal"

        return self.annotated_tickets(user, scope=scope), scope

    def base_tickets(self, user, scope="personal"):
        """Tickets visible to this user."""

        if scope == "personal":
            return Ticket.objects.filter(created_by=user).distinct()

        if scope == "department":         
            return Ticket.objects.filter(assignments__department__assigned_users__user=user).distinct()
        
        if scope == 'assigned':
            return Ticket.objects.filter(participants__user=user).distinct()

    def annotated_tickets(self, user, scope="personal"):
        """Tickets with last message info annotated."""
        last_msg = TicketMessage.objects.filter(ticket_id=OuterRef("pk")).order_by("-edited_at")
        return (
            self.base_tickets(user, scope=scope)
            .annotate(
                last_message_at=Subquery(last_msg.values("edited_at")[:1]),
                last_message_body=Subquery(last_msg.values("body")[:1]),
                last_message_sender_id=Subquery(last_msg.values("sender_id")[:1]),
                last_sender_is_staff=Subquery(last_msg.values("sender__is_staff")[:1]),
                last_sender_first=Subquery(last_msg.values("sender__first_name")[:1]),
                last_sender_last=Subquery(last_msg.values("sender__last_name")[:1]),
            )
        )

    def completed_tickets(self, qs):
        """Tickets that are completed/closed."""
        return qs.filter(status=Ticket.Status.CLOSED).order_by("-updated_at")

    def overdue_tickets(self, qs):
        """Tickets that are overdue for a response."""
        cutoff = timezone.now() - timedelta(days=7)
        return qs.filter(
            status__in=[Ticket.Status.OPEN, Ticket.Status.PENDING],
            last_message_at__isnull=False,
            last_message_at__lt=cutoff,
            last_sender_is_staff=False,
        ).order_by("-last_message_at")

    def active_tickets(self, qs, overdue):
        """Tickets that are active and not overdue."""
        return qs.filter(
            status__in=[Ticket.Status.OPEN, Ticket.Status.PENDING],
        ).exclude(
            id__in=overdue.values_list("id", flat=True)
        ).order_by("-updated_at")