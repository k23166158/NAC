from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.shortcuts import redirect
from django.views import View
from django.shortcuts import render

from tickets.forms.create_ticket import CreateTicketForm
from tickets.models import Ticket, TicketMessage, TicketAssigned


class CreateTicketView(LoginRequiredMixin, View):
    template_name = "create_ticket.html"
    login_url = "login"

    def get(self, request):
        return render(request, self.template_name, {"form": CreateTicketForm()})

    def post(self, request):
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
            TicketAssigned.objects.create(
                ticket=ticket,
                department=form.cleaned_data["department"],
            )

        return redirect("home")