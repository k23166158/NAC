from django.utils import timezone
from tickets.models import TicketMessage
from tickets.models.ticket_participant import TicketParticipant
from tickets.models import Ticket


def assign_staff_to_ticket(ticket, staff_user, *, added_by=None):
    """
    Assign a staff user to a ticket with forwarding side-effects.
    Returns (created: bool).
    """
    participant, created = TicketParticipant.objects.get_or_create(
        ticket=ticket,
        user=staff_user,
        defaults={"added_by": added_by} if added_by and hasattr(TicketParticipant, "added_by") else {},
    )

    if not created:
        return False

    TicketMessage.objects.create(
        ticket=ticket,
        sender=None,
        body=f"{staff_user.get_full_name()} was added to the ticket.",
    )

    Ticket.objects.filter(id=ticket.id).update(updated_at=timezone.now())
    return True
