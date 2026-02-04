from urllib.parse import quote

from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect
from django.views import View

from ..forms import ForwardTicketForm
from ..models import Ticket
from ..models.ticket_participant import TicketParticipant


def _q(value):
    """URL-encode a value as a string."""
    return quote(str(value))


def _ticket_redirect(return_tab, ticket_uuid, **params):
    """Redirect to ticket thread with query params."""
    base = f"/tickets/{_q(ticket_uuid)}/"
    params_with_tab = {"tab": return_tab, "open": ticket_uuid, **params}
    extra = "&".join(f"{k}={_q(v)}" for k, v in params_with_tab.items())
    return redirect(f"{base}?{extra}")


def _has_field(model, field_name):
    """Return True if model has a field with the given name."""
    return any(f.name == field_name for f in model._meta.fields)


def _err(form):
    """Return best-effort email error message from a form."""
    return form.errors.get("email", ["Email failed to forward."])[0]


class ForwardTicketView(View):
    """Forward a ticket to another staff member (POST-only)."""

    def _forbidden(self):
        """Return a 403 response for unauthorized forwards."""
        return HttpResponseForbidden("You don't have permission to forward tickets.")

    def _ticket(self, ticket_uuid):
        """Fetch a ticket by UUID or 404."""
        return get_object_or_404(Ticket, uuid=ticket_uuid)

    def _defaults(self, request):
        """Build defaults dict for TicketParticipant creation."""
        return {"added_by": request.user} if _has_field(TicketParticipant, "added_by") else {}

    def post(self, request, ticket_id):
        """Handle POST to forward a ticket to a staff user."""
        if not request.user.is_authenticated or not request.user.is_staff:
            return self._forbidden()
        ticket = self._ticket(ticket_id)
        rt = request.POST.get("return_tab", "active")
        form = ForwardTicketForm(request.POST)
        if not form.is_valid():
            return _ticket_redirect(rt, ticket.uuid, fwd="err", tid=ticket.uuid, msg=_err(form))
        staff_user = form.get_user()
        if staff_user.id == request.user.id:
            return _ticket_redirect(rt, ticket.uuid, fwd="err", tid=ticket.uuid, msg="You cannot forward a ticket to yourself.")
        TicketParticipant.objects.get_or_create(ticket=ticket, user=staff_user, defaults=self._defaults(request))
        return _ticket_redirect(rt, ticket.uuid, fwd="ok", tid=ticket.uuid, email=staff_user.email)
