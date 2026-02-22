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
