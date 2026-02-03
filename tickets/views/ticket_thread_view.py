from django.views.generic import DetailView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404
from ..models import Ticket, TicketMessage

class TicketThreadView(LoginRequiredMixin, DetailView):
    """View to display the thread of messages of tickets."""
    model = Ticket
    template_name = 'tickets/ticket_thread.html'
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

    def get_context_data(self, **kwargs):
        """Add ticket messages to the context."""
        context = super().get_context_data(**kwargs)
        messages = self.get_messages_queryset()

        context["first_message"] = self.get_first_message(messages)
        context["messages"] = self.get_reply_messages(messages)
        context["last_user_message_id"] = self.get_last_user_message_id(messages)

        context["edit_message"] = self.get_edit_message()

        return context

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

    def handle_add_action(self, request):
        """Handle adding a new message."""
        body = request.POST.get('body')
        if body:
            TicketMessage.objects.create(
                ticket=self.object,
                sender=request.user,
                body=body
            )

    def post(self, request, *args, **kwargs):
        """Handle POST actions: add, update, delete, or edit a message."""
        self.object = self.get_object()
        action = request.POST.get("action")

        if action == "delete":
            self.handle_delete_action(request)
            return self.get(request, *args, **kwargs)
        if action == "update":
            self.handle_update_action(request)
            return self.get(request, *args, **kwargs)
        if action == "edit":
            return self.get(request, *args, **kwargs)
        
        self.handle_add_action(request)
        return self.get(request, *args, **kwargs)