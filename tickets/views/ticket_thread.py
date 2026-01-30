from django.views.generic import DetailView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from ..models import Ticket, TicketMessage

class TicketThreadView(LoginRequiredMixin, DetailView):
    """View to display the thread of messages of tickets."""
    model = Ticket
    template_name = 'tickets/ticket_thread.html'
    context_object_name = 'ticket'

    def get_messages_queryset(self):
        """Get the queryset for ticket messages."""
        return TicketMessage.objects.filter(ticket=self.object).order_by("timestamp")

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
        """Get context data for the ticket thread view."""
        context = super().get_context_data(**kwargs)
        messages = self.get_messages_queryset()
        context["first_message"] = self.get_first_message(messages)
        context["messages"] = self.get_reply_messages(messages)
        context["last_user_message_id"] = self.get_last_user_message_id(messages)
        return context

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
        """Post request handler to add a new message or delete one."""
        self.object = self.get_object()
        action = request.POST.get("action")
        if action == "delete":
            self.handle_delete_action(request)
        else:
            self.handle_add_action(request)
        return self.get(request, *args, **kwargs)