"""
Management command to seed the database with demo data.

Existing records are left untouched, if a create fails (e.g., due to duplicates), generation continues.
"""

from faker import Faker
from random import choice, randint
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

from tickets.models import Department, Ticket, TicketMessage, TicketAssigned


DEPARTMENT_FIXTURES = [
    "NMES",
    "Finance",
    "HR",
    "Support",
    "Art and Humanities",
    "Classics",
]


class Command(BaseCommand):
    """
    Seed the tickets app with sample data.

    Creates demo users and then seeds departments, tickets, messages, and
    assignments to departments.
    """

    USER_COUNT = 30
    TICKET_COUNT = 60
    MAX_MESSAGES_PER_TICKET = 4
    DEFAULT_PASSWORD = "Password123"
    help = "Seeds the database with sample data"

    def __init__(self, *args, **kwargs):
        """Initialize the command with a locale-specific Faker instance."""
        super().__init__(*args, **kwargs)
        self.faker = Faker("en_GB")
        self.User = get_user_model()

    def handle(self, *args, **options):
        """Django entrypoint for the command."""
        self.create_users()
        self.users = list(self.User.objects.all())
        self.create_departments()
        self.departments = list(Department.objects.all())
        self.create_tickets()
        self.tickets = list(Ticket.objects.all())
        self.create_messages()
        self.create_assignments()
        self.stdout.write(self.style.SUCCESS("Seeding complete."))

    def create_users(self):
        """Generate demo users up to USER_COUNT."""
        while self.User.objects.count() < self.USER_COUNT:
            self.try_create_user(self.generate_user_data())

    def generate_user_data(self):
        """Generate a single user's fields using Faker."""
        first = self.faker.first_name()
        last = self.faker.last_name()
        return {
            "username": self.create_username(first, last),
            "email": self.create_email(first, last),
            "first_name": first,
            "last_name": last,
            "bio": self.faker.sentence(nb_words=10),
        }

    def try_create_user(self, data):
        """Attempt to create a user; ignore errors (e.g., duplicates)."""
        try:
            self.create_user(data)
        except Exception:
            pass

    def create_user(self, data):
        """Create a user with DEFAULT_PASSWORD."""
        self.User.objects.create_user(
            username=data["username"],
            email=data["email"],
            password=self.DEFAULT_PASSWORD,
            first_name=data["first_name"],
            last_name=data["last_name"],
            bio=data["bio"],
        )

    def create_departments(self):
        """Create standard departments."""
        if not self.User.objects.exists():
            return
        creator = self.User.objects.first()
        for name in DEPARTMENT_FIXTURES:
            self.try_create_department(name, creator)

    def try_create_department(self, name, created_by):
        """Attempt to create a department; ignore errors (e.g., duplicates)."""
        try:
            Department.objects.get_or_create(name=name, defaults={"created_by": created_by})
        except Exception:
            pass

    def create_tickets(self):
        """Create random tickets up to TICKET_COUNT."""
        while Ticket.objects.count() < self.TICKET_COUNT and self.User.objects.exists():
            self.try_create_ticket(self.generate_ticket_data())

    def generate_ticket_data(self):
        """Generate random ticket fields."""
        return {
            "title": self.faker.sentence(nb_words=6).rstrip("."),
            "status": choice([Ticket.Status.OPEN, Ticket.Status.PENDING, Ticket.Status.CLOSED]),
            "created_by": choice(self.users),
        }

    def try_create_ticket(self, data):
        """Attempt to create a ticket; ignore errors."""
        try:
            Ticket.objects.create(**data)
        except Exception:
            pass

    def create_messages(self):
        """Create at least one message (and sometimes more) for each ticket."""
        if not self.tickets:
            return
        for ticket in self.tickets:
            self.create_messages_for_ticket(ticket)

    def create_messages_for_ticket(self, ticket):
        """Create between 1 and MAX_MESSAGES_PER_TICKET messages for a ticket."""
        message_count = randint(1, self.MAX_MESSAGES_PER_TICKET)
        for _ in range(message_count):
            self.try_create_message(ticket, choice(self.users))

    def try_create_message(self, ticket, sender):
        """Attempt to create a TicketMessage; ignore errors."""
        try:
            TicketMessage.objects.create(
                ticket=ticket,
                body=self.faker.paragraph(nb_sentences=3),
                sender=sender,
            )
        except Exception:
            pass

    def create_assignments(self):
        """Assign each ticket to a random department (one assignment per ticket)."""
        if not self.tickets or not self.departments:
            return
        for ticket in self.tickets:
            self.try_assign_ticket(ticket, choice(self.departments))

    def try_assign_ticket(self, ticket, department):
        """Attempt to create a TicketAssigned row; ignore errors (unique_together)."""
        try:
            TicketAssigned.objects.get_or_create(ticket=ticket, department=department)
        except Exception:
            pass

    def create_username(self, first_name, last_name):
        """Construct a simple username from first and last names."""
        base = (first_name[0] + last_name).lower()
        return base[:30]

    def create_email(self, first_name, last_name):
        """Construct a simple example email address."""
        return f"{first_name}.{last_name}{randint(1, 9999)}@example.org".lower()