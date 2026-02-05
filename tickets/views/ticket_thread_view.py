from django.views.generic import DetailView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404
from django.contrib.auth import get_user_model
from django.utils import timezone
from requests import request
from tickets.helpers.ticket_assignment import assign_staff_to_ticket


from tickets.models.ticket_participant import TicketParticipant
from ..models import Ticket, TicketMessage

User = get_user_model()

class TicketThreadView(LoginRequiredMixin, DetailView):
    """View to display the thread of messages of tickets."""
    model = Ticket
    template_name = 'ticket_thread.html'
    context_object_name = 'ticket'
    slug_url_kwarg = 'uuid'
    slug_field = 'uuid'

    def get_messages_queryset(self):
        """Get the queryset for ticket messages."""
        return TicketMessage.objects.filter(ticket=self.object).order_by("created_at")

    def get_first_message(self, messages):
        """Extract the first message."""
        return messages.first()

    def get_reply_messages(self, messages):
        """Extract reply messages (excluding the first)."""
        return messages[1:] if messages.count() > 1 else []

    def get_last_user_message_id(self, messages):
        """Get the ID of the last visible user message."""
        last_user_message = messages.filter(sender=self.request.user, hidden=False).last()
        return last_user_message.id if last_user_message else None
    
    def get_ticket_staff(self):
        return [
            p.user for p in self.object.participants.select_related("user")
        ]

    def get_available_staff(self, current_staff):
        current_ids = [u.id for u in current_staff]
        return User.objects.filter(is_staff=True).exclude(id__in=current_ids)


    def get_context_data(self, **kwargs):
        """Add ticket messages to the context."""
        context = super().get_context_data(**kwargs)
        messages = self.get_messages_queryset()

        current_staff = self.get_ticket_staff()

        context["staff"] = current_staff
        context["available_staff"] = self.get_available_staff(current_staff)

        context["first_message"] = self.get_first_message(messages)
        context["messages"] = self.get_reply_messages(messages)
        context["last_user_message_id"] = self.get_last_user_message_id(messages)

        context["edit_message"] = self.get_edit_message()

        return context
    
    def touch_ticket(self):
        """Update the ticket's updated_at timestamp."""
        Ticket.objects.filter(id=self.object.id).update(updated_at=timezone.now())

    def get_edit_message(self):
        """Return the message being edited, if any."""
        message_id = self.request.POST.get("message_id")
        if self.request.POST.get("action") == "edit" and message_id:
            return get_object_or_404(
                TicketMessage,
                id=message_id,
                ticket=self.object,
                sender=self.request.user,
                hidden=False,
            )
        return None

    def handle_delete_action(self, request):
        """Handle deleting a message by hiding it."""
        message_id = request.POST.get("message_id")
        message = get_object_or_404(
            TicketMessage,
            id=message_id,
            ticket=self.object,
            sender=request.user,  # security: only delete own messages
        )
        message.hidden = True
        message.save()
        self.touch_ticket()

    def handle_update_action(self, request):
        """Handle updating an existing message."""
        message_id = request.POST.get("message_id")
        message = get_object_or_404(
            TicketMessage,
            id=message_id,
            ticket=self.object,
            sender=request.user,
            hidden=False,
        )
        body = request.POST.get("body")
        if body:
            message.body = body
            message.edited = True
            message.save()
            self.touch_ticket()

    def handle_add_action(self, request):
        """Handle adding a new message."""
        body = request.POST.get('body')
        if body:
            TicketMessage.objects.create(
                ticket=self.object,
                sender=request.user,
                body=body
            )
            self.touch_ticket()

    def handle_staff_change(self, request):
        user_id = request.POST.get("user_id")
        action = request.POST.get("action")

        if not user_id:
            return

        user = get_object_or_404(User, id=user_id, is_staff=True)

        if action == "add":
            assign_staff_to_ticket(
                ticket=self.object,
                staff_user=user,
                added_by=request.user,
            )

        elif action == "remove":
            TicketParticipant.objects.filter(
                ticket=self.object,
                user=user,
            ).delete()

            TicketMessage.objects.create(
                ticket=self.object,
                sender=None,
                body=f"{user.get_full_name()} was removed from the ticket.",
            )

        self.touch_ticket()



    def dispatch_post_action(self, action, request):
        """Dispatch POST action to the appropriate handler."""
        handlers = {
            "delete": lambda: self.handle_delete_action(request),
            "update": lambda: self.handle_update_action(request),
            "close_ticket": self.handle_close_ticket_action,
            "edit": lambda: None,
        }
        handlers.get(action, lambda: self.handle_add_action(request))()

    def post(self, request, *args, **kwargs):
        """Handle POST actions for the ticket thread."""
        self.object = self.get_object()
        action = request.POST.get("action")

        if action in {"add", "remove"}:
            self.handle_staff_change(request)
            return self.get(request, *args, **kwargs)

        self.dispatch_post_action(action, request)
        return self.get(request, *args, **kwargs)

    def handle_close_ticket_action(self):
        """Close the ticket."""
        if self.object.status != Ticket.Status.CLOSED:
            self.object.status = Ticket.Status.CLOSED
            self.object.closed_at = timezone.now()
            self.object.save()
            self.touch_ticket()