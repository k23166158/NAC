from asyncio import Handle
from urllib.parse import quote

from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect
from django.views import View

from ..forms import ForwardTicketForm
from ..models import Ticket
from ..models.ticket_participant import TicketParticipant


def _ticket_redirect(rt, ticket_id, **p):
    """Build a redirect back to the ticket list preserving tab/open and extra params.

    Returns a Django `HttpResponseRedirect` to the root with the provided query
    parameters encoded. Kept at module-level so `ForwardTicketView.post` stays short.
    """
    return redirect(f"/?tab={quote(rt)}&open={ticket_id}&" + "&".join(f"{k}={quote(str(v))}" for k, v in p.items()))


class ForwardTicketView(View):
    """View to forward a ticket to another staff member."""

    def post(self, request, ticket_id):
        """Forward a ticket to another staff member via POST.
        Returns 403 for unauthorized users.
        """
        if not (request.user.is_authenticated and request.user.is_staff):
            return HttpResponseForbidden("You don't have permission to forward tickets.")
        ticket = get_object_or_404(Ticket, pk=ticket_id)
        form = ForwardTicketForm(request.POST)
        rt = request.POST.get("return_tab", "active")
        if not form.is_valid():
            return _ticket_redirect(rt, ticket.id, fwd="err", tid=ticket.id, msg=form.errors.get("email", ["Email failed to forward."])[0])
        staff_user = form.get_user()
        if staff_user.id == request.user.id:
            return _ticket_redirect(rt, ticket.id, fwd="err", tid=ticket.id, msg="You cannot forward a ticket to yourself.")
        TicketParticipant.objects.get_or_create(ticket=ticket, user=staff_user, defaults={"added_by": request.user} if "added_by" in [f.name for f in TicketParticipant._meta.fields] else {})
        return _ticket_redirect(rt, ticket.id, fwd="ok", tid=ticket.id, email=staff_user.email)
