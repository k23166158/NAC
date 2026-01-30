from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from django.views import View

from ..forms import ForwardTicketForm
from ..models import Ticket
from ..models.ticket_participant import TicketParticipant


class ForwardTicketView(View):
    """View to forward a ticket to another staff member."""
    def post(self, request, ticket_id):
        """Handle forwarding a ticket to another staff member."""
        if not request.user.is_authenticated or not request.user.is_staff:
            messages.error(request, "You don't have permission to forward tickets.")
            return redirect("home")
        ticket = get_object_or_404(Ticket, pk=ticket_id)
        form = ForwardTicketForm(request.POST)
        if not form.is_valid():
            messages.error(request, form.errors.get("email", ["Invalid email."])[0])
            return redirect("home")
        staff_user = form.get_user()
        TicketParticipant.objects.get_or_create(ticket=ticket, user=staff_user, defaults={"added_by": request.user})
        messages.success(request, f"Forwarded to {staff_user.email}.")
        return redirect("home")
