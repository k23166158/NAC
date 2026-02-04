from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.shortcuts import redirect, render
from django.views import View

from tickets.forms.ticket_create import CreateTicketForm
from tickets.models import Ticket, TicketMessage, TicketAssigned


class CreateTicketView(LoginRequiredMixin, View):
    """View to create a ticket and its initial message."""
    template_name = "create_ticket.html"
    login_url = "login"

    def get(self, request):
        """Render the ticket creation form."""
        return render(request, self.template_name, {"form": CreateTicketForm()})

    def post(self, request):
        """Validate and create Ticket + TicketMessage + TicketAssigned rows."""
        form = CreateTicketForm(request.POST)
        if not form.is_valid():
            return render(request, self.template_name, {"form": form})

        with transaction.atomic():
            ticket = Ticket.objects.create(
                title=form.cleaned_data["title"],
                created_by=request.user,
            )
            TicketMessage.objects.create(
                ticket=ticket,
                body=form.cleaned_data["body"],
                sender=request.user,
            )
            for dept in form.cleaned_data["departments"]:
                TicketAssigned.objects.create(ticket=ticket, department=dept)

        return redirect("home")