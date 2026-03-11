from django.utils import timezone
from tickets.models import TicketMessage
from tickets.models.ticket_participant import TicketParticipant
from tickets.models import Ticket


def assign_staff_to_ticket(ticket, staff_user, *, added_by=None):
    """Assign a staff user to a ticket with forwarding side-effects.Returns (created: bool)."""
    participant, created = TicketParticipant.objects.get_or_create(
        ticket=ticket,
        user=staff_user,
        defaults={"added_by": added_by} if added_by and hasattr(TicketParticipant, "added_by") else {},
    )
    if not created and participant.removed_self:
        participant.removed_self = False
        participant.save()
    if not created: return False
    TicketMessage.objects.create(ticket=ticket,sender=None,body=f"{staff_user.get_full_name()} was added to the ticket.",)
    Ticket.objects.filter(id=ticket.id).update(updated_at=timezone.now())
    return True

from tickets.models import TicketParticipant, TicketMessage
from tickets.models.ticket_department import TicketDepartment

def _restore_participant(participant):
    """Restore a participant who had previously removed themselves from the ticket."""
    if participant.removed_self:
        participant.removed_self = False
        participant.save()

def _add_department_member(ticket, user):
    """Add a user as a participant to the ticket if not already added."""
    participant, created = TicketParticipant.objects.get_or_create(
        ticket=ticket,
        user=user,
    )
    if not created:
        _restore_participant(participant)

def assign_department_to_ticket(ticket, department, added_by):
    """Assign a department to a ticket and add its members."""
    TicketDepartment.objects.get_or_create(
        ticket=ticket,
        department=department,
    )
    for user in department.members.all():
        _add_department_member(ticket, user)
    TicketMessage.objects.create(
        ticket=ticket,
        sender=None,
        body=f"The {department.name} department was added to the ticket.",
    )

    Ticket.objects.filter(id=ticket.id).update(updated_at=timezone.now())
