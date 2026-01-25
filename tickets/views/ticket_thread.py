from django.views.generic import DetailView
from django.contrib.auth.mixins import LoginRequiredMixin
from ..models import Ticket, TicketMessage

class TicketThreadView(LoginRequiredMixin, DetailView):
    """View to display the thread of messages of tickets."""

    model = Ticket
    template_name = 'tickets/ticket_thread.html'
    context_object_name = 'ticket'

    def get_context_data(self, **kwargs):
        """Add ticket messages to the context."""
        context = super().get_context_data(**kwargs)
        context['messages'] = TicketMessage.objects.filter(ticket=self.object)
        return context
    