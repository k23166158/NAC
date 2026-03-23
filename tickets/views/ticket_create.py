from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect, render
from django.views import View

from tickets.forms.ticket_create import CreateTicketForm
from tickets.models import Ticket


class CreateTicketView(LoginRequiredMixin, View):
    """View to create a ticket and its initial message."""
    login_url = "login"

    def get(self, request):
        """Render the ticket creation form."""
        return render(request, "create_ticket.html", {"form": CreateTicketForm()})

    def post(self, request):
        """Validate and create ticket data, then redirect home."""
        form = CreateTicketForm(request.POST, request.FILES)
        if not form.is_valid():
            return render(request, "create_ticket.html", {"form": form})

        files = request.FILES.getlist("attachments") if request.FILES else None
        Ticket.create_with_initial_message(
            creator=request.user,
            cleaned_data=form.cleaned_data,
            files=files,
        )
        return redirect("home")
