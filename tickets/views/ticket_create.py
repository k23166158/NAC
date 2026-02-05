from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.shortcuts import redirect, render
from django.views import View

from tickets.forms.ticket_create import CreateTicketForm
from tickets.models import Ticket, TicketMessage, TicketAssigned


def build_create_ticket_form(post_data=None):
    """Return a CreateTicketForm instance for GET or POST."""
    return CreateTicketForm(post_data) if post_data is not None else CreateTicketForm()


def render_create_ticket(request, form):
    """Render the create ticket page with the given form."""
    return render(request, "create_ticket.html", {"form": form})


def create_ticket_objects(user, cleaned):
    """Create Ticket, TicketMessage, and TicketAssigned objects from form data."""
    with transaction.atomic():
        ticket = Ticket.objects.create(title=cleaned["title"], created_by=user)
        TicketMessage.objects.create(ticket=ticket, body=cleaned["body"], sender=user)
        for dept in cleaned["departments"]:
            TicketAssigned.objects.create(ticket=ticket, department=dept)
    return ticket


class CreateTicketView(LoginRequiredMixin, View):
    """View to create a ticket and its initial message."""
    login_url = "login"

    def get(self, request):
        """Render the ticket creation form."""
        return render_create_ticket(request, build_create_ticket_form())

    def post(self, request):
        """Validate and create ticket data, then redirect home."""
        form = build_create_ticket_form(request.POST)
        if not form.is_valid():
            return render_create_ticket(request, form)
        create_ticket_objects(request.user, form.cleaned_data)
        return redirect("home")