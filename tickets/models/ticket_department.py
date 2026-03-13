# tickets/models/ticket_department.py
from django.db import models
from .ticket import Ticket
from .department import Department


class TicketDepartment(models.Model):
    """Model representing the assignment of a ticket to a department."""
    ticket = models.ForeignKey(
        Ticket,
        on_delete=models.CASCADE,
        related_name="ticket_departments",
    )
    department = models.ForeignKey(
        Department,
        on_delete=models.CASCADE,
        related_name="ticket_departments",
    )

    added_on = models.DateTimeField(auto_now_add=True)

    class Meta:
        """Meta options for the TicketDepartment model."""
        unique_together = ("ticket", "department")

    @classmethod
    def assign_department(cls, ticket, department, *, added_by=None):
        """Assign a department with standard ticket side effects."""
        from tickets.helpers.ticket_assignment import assign_department_to_ticket

        return assign_department_to_ticket(
            ticket=ticket,
            department=department,
            added_by=added_by,
        )

    @classmethod
    def remove_department(cls, ticket, department, removed_by=None):
        """Remove a ticket-department relation and log system message."""
        from .ticket_message import TicketMessage
        from tickets.models.notification import Notification
        from tickets.helpers.notifications import create_notification

        members = list(department.members.all())
        cls.objects.filter(ticket=ticket, department=department).delete()
        TicketMessage.create_system_message(ticket, f"{department.name} was removed from the ticket.")
        for user in members:
            if user != removed_by:
                create_notification(
                    user=user,
                    actor=removed_by,
                    notification_type=Notification.NotificationType.DEPT_REMOVED,
                    link=f"/tickets/{ticket.uuid}/",
                    target_object=ticket,
                )
