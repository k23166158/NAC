from urllib.parse import quote

from django.http import HttpResponseForbidden
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from django.views import View

from tickets.forms import ForwardTicketForm
from tickets.models import Ticket
from tickets.models.notification import Notification
from tickets.models.ticket_participant import TicketParticipant
from tickets.models.ticket_message import TicketMessage
from tickets.helpers.notifications import create_notification

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

class ForwardTicketView(LoginRequiredMixin, View):
    """Forward a ticket to another staff member (POST-only)."""

    def _forbidden(self):
        """Return a 403 response for unauthorized forwards."""
        return HttpResponseForbidden("You don't have permission to forward tickets.")

    def _ticket(self, ticket_uuid):
        """Fetch a ticket by UUID or 404."""
        return get_object_or_404(Ticket, uuid=ticket_uuid)

    def _defaults(self, request):
        """Build defaults dict for TicketParticipant creation."""
        return TicketParticipant.defaults_for_actor(request.user) if _has_field(TicketParticipant, "added_by") else {}
    
    def touch_ticket(self, ticket):
        """Update the ticket's updated_at timestamp."""
        ticket.touch()

    def post(self, request, ticket_id):
        """Handle POST to forward a ticket to a staff user."""
        if not request.user.is_authenticated or not request.user.is_staff:
            return self._forbidden()

        ticket, rt, form = self._ticket(ticket_id), request.POST.get("return_tab", "active"), ForwardTicketForm(request.POST)
        if not form.is_valid():
            return self._redirect_error(ticket, rt, _err(form))

        staff_user = form.get_user()
        if self._invalid_forward(request.user, ticket, staff_user):
            return self._redirect_error(ticket, rt, self._forward_error_msg(request.user, ticket, staff_user))

        self._forward_ticket(ticket, staff_user)
        return _ticket_redirect(rt, ticket.uuid, fwd="ok", tid=ticket.uuid, email=staff_user.email)

    def _redirect_error(self, ticket, rt, msg):
        """Direct to ticket with error message."""
        return _ticket_redirect(rt, ticket.uuid, fwd="err", tid=ticket.uuid, msg=msg)

    def _invalid_forward(self, user, ticket, staff_user):
        """Check if forwarding to the given staff user is invalid."""
        return staff_user.id == user.id or TicketParticipant.has_participant(ticket, staff_user)

    def _forward_error_msg(self, user, ticket, staff_user):
        """Generate an error message for invalid forwards."""
        if staff_user.id == user.id:
            return "You cannot forward a ticket to yourself."
        return "That staff member already has access to this ticket."

    def _forward_ticket(self, ticket, staff_user):
        """Forward the ticket to the given staff user."""
        TicketParticipant.add_participant(
            ticket,
            staff_user,
            actor=self.request.user,
            defaults=self._defaults(self.request),
        )
        TicketMessage.create_system_message(
            ticket,
            f"Ticket forwarded to {staff_user.full_name()}",
        )
        self.touch_ticket(ticket)
        create_notification(
            user=staff_user,
            actor=self.request.user,
            notification_type=Notification.NotificationType.TICKET_FORWARDED,
            link=f"/tickets/{ticket.uuid}/",
            target_object=ticket,
        )
