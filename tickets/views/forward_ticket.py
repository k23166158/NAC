from asyncio import Handle
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
        rt = request.POST.get("return_tab", "active")
        def r(**p):
            return redirect(f"/?tab={quote(rt)}&open={ticket.id}&" + "&".join(f"{k}={quote(str(v))}" for k,v in p.items()))
        if not form.is_valid():
            return r(fwd="err", tid=ticket.id, msg=form.errors.get("email", ["Email failed to forward."])[0])
        staff_user = form.get_user()
        if staff_user.id == request.user.id:
            return r(fwd="err", tid=ticket.id, msg="You cannot forward a ticket to yourself.")
        defaults = {"added_by": request.user} if "added_by" in [f.name for f in TicketParticipant._meta.fields] else {}
        TicketParticipant.objects.get_or_create(ticket=ticket, user=staff_user, defaults=defaults)
        return r(fwd="ok", tid=ticket.id, email=staff_user.email)
