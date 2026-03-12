from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.shortcuts import redirect, render
from django.views import View

from tickets.forms.ticket_create import CreateTicketForm
from tickets.models import Ticket, TicketMessage, TicketAssigned, TicketMessageAttachment


def build_create_ticket_form(post_data=None, file_data=None):
    """Return a CreateTicketForm instance for GET or POST."""
    return CreateTicketForm(post_data, file_data) if post_data is not None else CreateTicketForm()


def render_create_ticket(request, form):
    """Render the create ticket page with the given form."""
    return render(request, "create_ticket.html", {"form": form})


def build_assignments(ticket, departments):
    """Build TicketAssigned rows for selected departments (legacy compatibility)."""
    return [TicketAssigned(ticket=ticket, department=dept) for dept in departments]


def _build_attachment(ticket, message, file, user):
    """Build a TicketMessageAttachment object from an uploaded file."""
    return TicketMessageAttachment(
        ticket=ticket,
        message=message,
        file=file,
        original_name=file.name,
        content_type=file.content_type or "",
        size_bytes=file.size,
        uploaded_by=user,
    )


def create_attachments(ticket, message, files, user):
    """Create attachments for the given message from uploaded files."""
    if not files:
        return
    attachments = [_build_attachment(ticket, message, f, user) for f in files if f]
    if attachments:
        TicketMessageAttachment.objects.bulk_create(attachments)


def _create_ticket(user, cleaned):
    """Create and return a new ticket instance."""
    return Ticket.objects.create(
        title=cleaned["title"],
        created_by=user,
    )


def _create_first_message(ticket, user, cleaned):
    """Create and return the initial ticket message."""
    return TicketMessage.objects.create(
        ticket=ticket,
        body=cleaned["body"],
        sender=user,
    )


def _assign_departments(ticket, departments, user):
    """Persist legacy department assignments for the ticket."""
    TicketAssigned.objects.bulk_create(build_assignments(ticket, departments))


def create_ticket_objects(user, cleaned, files=None):
    """Create ticket, initial message, assignments, and attachments."""
    with transaction.atomic():
        ticket = _create_ticket(user, cleaned)
        message = _create_first_message(ticket, user, cleaned)
        _assign_departments(ticket, cleaned["departments"], user)
        create_attachments(ticket, message, files, user)
    return ticket


class CreateTicketView(LoginRequiredMixin, View):
    """View to create a ticket and its initial message."""
    login_url = "login"

    def get(self, request):
        """Render the ticket creation form."""
        return render_create_ticket(request, build_create_ticket_form())

    def post(self, request):
        """Validate and create ticket data, then redirect home."""
        form = build_create_ticket_form(request.POST, request.FILES)
        if not form.is_valid():
            return render_create_ticket(request, form)
        files = request.FILES.getlist('attachments') if request.FILES else None
        create_ticket_objects(request.user, form.cleaned_data, files)
        return redirect("home")