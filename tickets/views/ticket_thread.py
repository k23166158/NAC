from django.views.generic import DetailView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from ..models import Ticket, TicketMessage


class TicketThreadView(LoginRequiredMixin, DetailView):
    """View to display the thread of messages of tickets."""

    model = Ticket
    template_name = 'tickets/ticket_thread.html'
    context_object_name = 'ticket'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        messages = TicketMessage.objects.filter(
            ticket=self.object
        ).order_by("timestamp")

        last_user_message = (
            messages
            .filter(sender=self.request.user, hidden=False)
            .last()
        )

        context["messages"] = messages
        context["last_user_message_id"] = (
            last_user_message.id if last_user_message else None
        )

        return context
    
    def post(self, request, *args, **kwargs):
        """Post request handler to add a new message to the ticket thread."""

        self.object = self.get_object()

        action = request.POST.get("action")

        if action == "delete":
            message_id = request.POST.get("message_id")

            message = get_object_or_404(
                TicketMessage,
                id=message_id,
                ticket=self.object,
                sender=request.user,  # security: only delete own messages
            )

            message.hidden = True
            message.save()
            return self.get(request, *args, **kwargs)

        body = request.POST.get('body')
        if body:
            TicketMessage.objects.create(
                ticket=self.object,
                sender=request.user,
                body=body
            )
        return self.get(request, *args, **kwargs)