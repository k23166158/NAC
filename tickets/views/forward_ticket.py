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
        if not request.user.is_authenticated or not request.user.is_staff:
            return HttpResponseForbidden("You don't have permission to forward tickets.")

        ticket = get_object_or_404(Ticket, pk=ticket_id)
        form = ForwardTicketForm(request.POST)

        # preserve UI state
        return_tab = request.POST.get("return_tab", "active")

        def go_err(message: str):
            return redirect(
                f"/?tab={quote(return_tab)}&open={ticket.id}"
                f"&fwd=err&tid={ticket.id}&msg={quote(message)}"
            )

        def go_ok(email: str):
            return redirect(
                f"/?tab={quote(return_tab)}&open={ticket.id}"
                f"&fwd=ok&tid={ticket.id}&email={quote(email)}"
            )

        if not form.is_valid():
            msg = form.errors.get("email", ["Email failed to forward."])[0]
            return go_err(str(msg))

        staff_user = form.get_user()

        if staff_user.id == request.user.id:
            return go_err("You cannot forward a ticket to yourself.")

        TicketParticipant.objects.get_or_create(
            ticket=ticket,
            user=staff_user,
            defaults={"added_by": request.user} if "added_by" in [f.name for f in TicketParticipant._meta.fields] else {},
        )

        return go_ok(staff_user.email)
