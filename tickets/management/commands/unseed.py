from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from tickets.models import Ticket, Department, TicketParticipant

User = get_user_model()

class Command(BaseCommand):
    """Build automation command to unseed the database."""

    def handle(self, *args, **options):
        """
        Django entrypoint for the command.
        
        Deletes all data created by the seed command to allow for a fresh start.
        """
        print("Unseeding data...")
        Ticket.objects.all().delete()
        Department.objects.all().delete()
        User.objects.all().delete()
        TicketParticipant.objects.all().delete()
        print("Unseeding complete.")