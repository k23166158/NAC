from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.views import View

from tickets.models import Ticket
from tickets.views.ticket_thread_mixins import (
    TicketThreadAssignmentMixin,
    TicketThreadContextMixin,
)


class TicketThreadView(TicketThreadContextMixin, TicketThreadAssignmentMixin, LoginRequiredMixin, View):
    """Display and manage the thread of messages for a ticket."""

    model = Ticket
    template_name = "ticket_thread.html"

    def get(self, request, uuid):
        """Render the ticket thread page."""
        qs = Ticket._annotate_last_message_for_user(Ticket.objects.all(), request.user)
        self.ticket = get_object_or_404(qs, uuid=uuid)
        self.object = self.ticket
        self.ticket.mark_read_for(request.user)
        context = self.get_context_data()
        context["permission"] = self.ticket.can_edit(request.user)
        context["scope"] = request.GET.get("scope", "personal")
        context["back_to_url"] = self._back_to_url(request)
        context["back_to_label"] = self._back_to_label(context["back_to_url"])
        return render(request, self.template_name, context)

    def post(self, request, uuid):
        """Handle POST actions for the ticket thread."""
        qs = Ticket._annotate_last_message_for_user(Ticket.objects.all(), request.user)
        self.ticket = get_object_or_404(qs, uuid=uuid)
        self.object = self.ticket
        self.request = request
        if not self.ticket.can_edit(request.user):
            return HttpResponseForbidden("You don't have permission to do this.")
        action = request.POST.get("action")
        if action == "remind_staff":
            self._handle_remind_staff(request)
            return self.get(request, uuid)
        if action in {"add", "remove"} and not self.ticket.can_manage_assignments(request.user):
            return HttpResponseForbidden("Assignment changes are not allowed for this ticket.")
        return self._handle_add_remove(request, request.POST.get("target_type"))

    def _handle_remind_staff(self, request):
        """Handle sending a reminder to staff for an overdue ticket."""
        if not self.ticket.is_overdue:
            messages.error(request, "This ticket is not currently overdue.")
            return
        
        if self.ticket.send_reminder(actor=request.user):
            messages.success(request, "A reminder has been sent to the assigned staff.")
        else:
            messages.error(request, "A reminder was already sent within the last 24 hours.")

    def _handle_add_remove(self, request, target_type):
        """Route add/remove actions to the correct assignment handler."""
        if target_type:
            self.handle_assignment_change(request)
        else:
            self.handle_staff_change(request)
        return self.get(request, self.object.uuid)

    def get_context_data(self):
        """Build context for rendering the ticket thread template."""
        messages = self.get_messages_queryset()
        staff = self.get_ticket_staff()
        departments = self.get_ticket_departments()

        return {
            "ticket": self.object, "staff": staff, "available_staff": self.get_available_staff(staff),
            "ticket_departments": departments, "available_departments": self.get_available_departments(departments),
            "first_message": self.get_first_message(messages), "messages": self.get_reply_messages(messages),
            "last_user_message_id": self.get_last_user_message_id(messages), 
            "user_has_removed": self.ticket.user_has_removed_themselves(self.request.user),
            "can_manage_assignments": self.ticket.can_manage_assignments(self.request.user),
            "can_send_reminder": self.ticket.can_send_reminder(),
        }

    def _back_to_url(self, request):
        """Return the URL used by the thread page back link."""
        return request.GET.get("return_to") or f'{reverse("home")}?scope={request.GET.get("scope", "personal")}'

    @staticmethod
    def _back_to_label(back_to_url):
        """Return the back-link label for the current origin."""
        return "Back to tickets"