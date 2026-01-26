from datetime import timedelta

from django.shortcuts import render
from django.utils import timezone
from django.views import View
from django.db.models import OuterRef, Subquery

from ..models import Ticket, TicketMessage


class HomeView(View):
    def get(self, request):
        if not request.user.is_authenticated:
            return render(request, "landing.html")

        qs = self._annotated_tickets(request.user)
        overdue = self._overdue_tickets(qs)
        context = {
            "completed_tickets": self._completed_tickets(qs),
            "overdue_tickets": overdue,
            "active_tickets": self._active_tickets(qs, overdue),
        }
        return render(request, "home.html", context)

    def _annotated_tickets(self, user):
        last_msg = TicketMessage.objects.filter(
            ticket_id=OuterRef("pk")
        ).order_by("-timestamp")

        return (
            Ticket.objects
            .filter(created_by=user)
            .annotate(
                last_message_at=Subquery(last_msg.values("timestamp")[:1]),
                last_message_body=Subquery(last_msg.values("body")[:1]),
                last_message_sender_id=Subquery(last_msg.values("sender_id")[:1]),
                last_sender_is_staff=Subquery(last_msg.values("sender__is_staff")[:1]),
                last_sender_first=Subquery(last_msg.values("sender__first_name")[:1]),
                last_sender_last=Subquery(last_msg.values("sender__last_name")[:1]),
            )
        )

    def _completed_tickets(self, qs):
        return qs.filter(
            status=Ticket.Status.CLOSED
        ).order_by("-updated_at")

    def _overdue_tickets(self, qs):
        cutoff = timezone.now() - timedelta(days=7)
        return qs.filter(
            status__in=[Ticket.Status.OPEN, Ticket.Status.PENDING],
            last_message_at__isnull=False,
            last_message_at__lt=cutoff,
            last_sender_is_staff=False,
        ).order_by("-last_message_at")

    def _active_tickets(self, qs, overdue):
        return qs.filter(
            status__in=[Ticket.Status.OPEN, Ticket.Status.PENDING],
        ).exclude(
            id__in=overdue.values_list("id", flat=True)
        ).order_by("-updated_at")