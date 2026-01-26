from datetime import timedelta

from django.shortcuts import render
from django.utils import timezone
from django.views import View
from django.db.models import OuterRef, Subquery

from ..models import Ticket, TicketMessage


class HomeView(View):
    def get(self, request):
        """Render the home page with categorized tickets for the authenticated user."""
        if not request.user.is_authenticated:
            return render(request, "landing.html")

        cutoff = timezone.now() - timedelta(days=7)

        base = Ticket.objects.filter(created_by=request.user)

        # Subquery: latest message for each ticket (by timestamp desc)
        last_msg = TicketMessage.objects.filter(
            ticket_id=OuterRef("pk")
        ).order_by("-timestamp")

        qs = base.annotate(
            last_message_at=Subquery(last_msg.values("timestamp")[:1]),
            last_message_body=Subquery(last_msg.values("body")[:1]),
            last_message_sender_id=Subquery(last_msg.values("sender_id")[:1]),
            last_sender_is_staff=Subquery(last_msg.values("sender__is_staff")[:1]),
            last_sender_first=Subquery(last_msg.values("sender__first_name")[:1]),
            last_sender_last=Subquery(last_msg.values("sender__last_name")[:1]),
        )

        completed_tickets = qs.filter(status=Ticket.Status.CLOSED).order_by("-updated_at")

        # Overdue = last message exists AND it's older than 7 days AND last message was from user (not staff)
        overdue_tickets = qs.filter(
            status__in=[Ticket.Status.OPEN, Ticket.Status.PENDING],
            last_message_at__isnull=False,
            last_message_at__lt=cutoff,
            last_sender_is_staff=False,
        ).order_by("-last_message_at")

        active_tickets = qs.filter(
            status__in=[Ticket.Status.OPEN, Ticket.Status.PENDING],
        ).exclude(
            id__in=overdue_tickets.values_list("id", flat=True)
        ).order_by("-updated_at")

        return render(request, "home.html", {
            "active_tickets": active_tickets,
            "overdue_tickets": overdue_tickets,
            "completed_tickets": completed_tickets,
        })