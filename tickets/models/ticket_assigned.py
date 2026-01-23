from django.db import models
from .ticket import Ticket
from .department import Department


class TicketAssigned(models.Model):
    """Represents the assignment of a ticket to a specific department."""
    ticket = models.ForeignKey(
        Ticket,
        on_delete=models.CASCADE,
        related_name='assignments'
    )


    department = models.ForeignKey(
        Department,
        on_delete=models.CASCADE,
        related_name='assigned_tickets'
    )

    class Meta:
        """Meta options for the TicketAssigned model."""
        db_table = "ticket_assigned"
        verbose_name_plural = "Ticket Assignments"
        unique_together = ('ticket', 'department')

    def __str__(self):
        """String representation of the TicketAssigned instance."""
        return f"Assignment: Ticket #{self.ticket.id} -> {self.department.name}"