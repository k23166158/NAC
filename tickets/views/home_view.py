from datetime import timedelta

from django.db.models import Count, OuterRef, Subquery, Q, F
from django.shortcuts import render
from django.utils import timezone
from django.views import View
from django.db.models import Subquery, OuterRef, Count, Q, DateTimeField
from django.db.models.functions import Coalesce
from django.utils import timezone

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
        
        ctx = self.get_context(request, qs, scope, overdue)
        if self.is_admin(request.user):
            ctx.update(self.get_admin_stats())
            
        return render(request, "home_view.html", ctx)

    def get_context(self, request, qs, scope, overdue):
        """Build the base context dictionary for the view, with pagination for the lists."""
        from django.core.paginator import Paginator
        
        active_qs = self.active_tickets(qs, overdue)
        overdue_qs = overdue
        completed_qs = self.completed_tickets(qs)

        active_paginator = Paginator(active_qs, 10)
        active_page = active_paginator.get_page(request.GET.get('active_page', 1))

        overdue_paginator = Paginator(overdue_qs, 10)
        overdue_page = overdue_paginator.get_page(request.GET.get('overdue_page', 1))

        completed_paginator = Paginator(completed_qs, 10)
        completed_page = completed_paginator.get_page(request.GET.get('completed_page', 1))

        return {
            "scope": scope,
            "completed_tickets": completed_qs, # keep for counts if needed
            "overdue_tickets": overdue_qs,
            "active_tickets": active_qs,
            "active_tickets_page": active_page,
            "overdue_tickets_page": overdue_page,
            "completed_tickets_page": completed_page,
        }

    def get_admin_stats(self):
        """Returns extra admin statistics for the dashboard."""
        return {
            "total_tickets": Ticket.objects.count(),
            "tickets_by_status": self.tickets_by_status(),
            "total_users": User.objects.count(),
        }

    def is_admin(self, user):
        """Check if a user has admin privileges."""
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
        """Annotate the base ticket queryset with message metadata."""
        qs = self.base_tickets(user, scope=scope)
        qs = self._annotate_last_message(qs, user)
        return self._annotate_unread_count(qs, user)

    def _annotate_last_message(self, qs, user):
        """Annotate the queryset with details of the last message and last read timestamp."""
        last_msg = TicketMessage.objects.filter(ticket_id=OuterRef("pk")).order_by("-edited_at")
        last_read = TicketParticipant.objects.filter(ticket=OuterRef("pk"),user=user).values("last_read_at")[:1]
        return qs.annotate(
            last_message_at=Subquery(last_msg.values("edited_at")[:1]),
            last_message_body=Subquery(last_msg.values("body")[:1]),
            last_message_sender_id=Subquery(last_msg.values("sender_id")[:1]),
            last_sender_is_staff=Subquery(last_msg.values("sender__is_staff")[:1]),
            last_sender_first=Subquery(last_msg.values("sender__first_name")[:1]),
            last_sender_last=Subquery(last_msg.values("sender__last_name")[:1]),
            user_last_read_at=Subquery(last_read, output_field=DateTimeField()),
        )
    
    def _annotate_unread_count(self, qs, user):
        """Annotate the queryset with the count of unread messages for the user."""
        return qs.annotate(
            unread_count=Count(
                "messages",
                filter=Q(messages__edited_at__gt=Coalesce(
                    F("user_last_read_at"),
                    timezone.make_aware(timezone.datetime.min)
                )) & ~Q(messages__sender=user)
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
