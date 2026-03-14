from django.utils import timezone
from tickets.models import TicketMessage
from tickets.models.ticket_participant import TicketParticipant
from tickets.models import Ticket
from tickets.models.notification import Notification
from tickets.helpers.notifications import create_notification


def _participant_defaults(added_by):
    """Return defaults for TicketParticipant.get_or_create."""
    if not added_by or not hasattr(TicketParticipant, "added_by"):
        return {}
    return {"added_by": added_by}


def _touch_ticket(ticket):
    """Update the ticket updated_at timestamp."""
    Ticket.objects.filter(id=ticket.id).update(updated_at=timezone.now())


def _staff_added_message(ticket, staff_user):
    """Create a system message for staff assignment."""
    TicketMessage.objects.create(
        ticket=ticket,
        sender=None,
        body=f"{staff_user.get_full_name()} was added to the ticket.",
    )


def _notify_staff_assigned(ticket, staff_user, added_by):
    """Notify a staff user that they were added to a ticket."""
    create_notification(
        user=staff_user,
        actor=added_by,
        notification_type=Notification.NotificationType.STAFF_ASSIGNED,
        link=f"/tickets/{ticket.uuid}/",
        target_object=ticket,
    )


def assign_staff_to_ticket(ticket, staff_user, *, added_by=None):
    """Assign a staff user to a ticket with forwarding side-effects.Returns (created: bool)."""
    participant, created = TicketParticipant.objects.get_or_create(
        ticket=ticket,
        user=staff_user,
        defaults=_participant_defaults(added_by),
    )
    if not created and participant.removed_self:
        participant.removed_self = False
        participant.save()
    if not created:
        return False
    _staff_added_message(ticket, staff_user)
    _touch_ticket(ticket)
    _notify_staff_assigned(ticket, staff_user, added_by)
    return created

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

def _ensure_department_assigned(ticket, department):
    """Ensure a TicketDepartment row exists."""
    TicketDepartment.objects.get_or_create(ticket=ticket, department=department)


def _department_added_message(ticket, department):
    """Create a system message for department assignment."""
    TicketMessage.objects.create(
        ticket=ticket,
        sender=None,
        body=f"The {department.name} department was added to the ticket.",
    )


def _notify_department_assigned(ticket, department, added_by):
    """Notify department members that their department was assigned to a ticket."""
    recipients = [u for u in department.members.all() if u != added_by]
    for user in recipients:
        create_notification(
            user=user,
            actor=added_by,
            notification_type=Notification.NotificationType.DEPT_ASSIGNED,
            link=f"/tickets/{ticket.uuid}/",
            target_object=ticket,
        )


def assign_department_to_ticket(ticket, department, added_by):
    """Assign a department to a ticket and add its members."""
    _ensure_department_assigned(ticket, department)
    for user in department.members.all():
        _add_department_member(ticket, user)
    _department_added_message(ticket, department)
    _touch_ticket(ticket)
    _notify_department_assigned(ticket, department, added_by)
