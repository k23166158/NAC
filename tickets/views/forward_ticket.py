from urllib.parse import quote

from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect
from django.views import View

from ..forms import ForwardTicketForm
from ..models import Ticket
from ..models.ticket_participant import TicketParticipant


class ForwardTicketView(View):
    """View to forward a ticket to another staff member."""

    def post(self, request, ticket_id):
        # Must be logged in + staff
        if not request.user.is_authenticated or not request.user.is_staff:
            return HttpResponseForbidden("You don't have permission to forward tickets.")

        ticket = get_object_or_404(Ticket, pk=ticket_id)
        form = ForwardTicketForm(request.POST)

        # Validation failed (email missing / not found / not staff)
        if not form.is_valid():
            msg = form.errors.get("email", ["Email failed to forward."])[0]
            return redirect(f"/?fwd=err&tid={ticket.id}&msg={quote(str(msg))}")

        staff_user = form.get_user()

        # Prevent forwarding to yourself
        if staff_user.id == request.user.id:
            return redirect(
                f"/?fwd=err&tid={ticket.id}&msg={quote('You cannot forward a ticket to yourself.')}"
            )

        # Add staff user as participant (idempotent)
        TicketParticipant.objects.get_or_create(
            ticket=ticket,
            user=staff_user,
            defaults={"added_by": request.user} if "added_by" in [
                f.name for f in TicketParticipant._meta.fields
            ] else {},
        )

        # Success popup
        return redirect(
            f"/?fwd=ok&tid={ticket.id}&email={quote(staff_user.email)}"
        )