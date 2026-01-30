"""
Management command to seed the database with demo data.

Existing records are left untouched—if a create fails (e.g., due
to duplicates) generation continues.
"""

from random import choice, randint
from faker import Faker
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

from tickets.models import Department, Ticket, TicketMessage, TicketAssigned


USER_FIXTURES = [
    {
        "username": "admin_kcl",
        "email": "admin.kcl@example.org",
        "first_name": "Amina",
        "last_name": "Khan",
        "password": "AdminPass123!",
        "superuser": True,
    },
    {
        "username": "staff_support",
        "email": "support.staff@example.org",
        "first_name": "James",
        "last_name": "Owen",
        "password": "StaffPass123!",
        "staff": True,
    },
    {
        "username": "staff_finance",
        "email": "finance.staff@example.org",
        "first_name": "Sarah",
        "last_name": "Patel",
        "password": "StaffPass456!",
        "staff": True,
    },
    {
        "username": "student_ali",
        "email": "ali.student@example.org",
        "first_name": "Ali",
        "last_name": "Hassan",
        "password": "StudentPass123!",
    },
    {
        "username": "student_maya",
        "email": "maya.student@example.org",
        "first_name": "Maya",
        "last_name": "Singh",
        "password": "StudentPass456!",
    },
    {
        "username": "student_zoe",
        "email": "zoe.student@example.org",
        "first_name": "Zoe",
        "last_name": "Williams",
        "password": "StudentPass789!",
    },
]

DEPARTMENT_FIXTURES = [
    "NMES",
    "Finance",
    "HR",
    "Support",
    "Art and Humanities",
    "Classics",
]


class Command(BaseCommand):
    """Build automation command to seed the database with data."""

    TICKET_COUNT = 40
    MAX_MESSAGES_PER_TICKET = 4
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
        """Attempt to create each predefined fixture user."""
        for data in USER_FIXTURES:
            self.try_create_user(data)

    def try_create_user(self, data):
        """Attempt to create a user; ignore errors (e.g., duplicates)."""
        try:
            self.create_user(data)
        except Exception:
            pass

    def create_user(self, data):
        """Create a user with the supplied password and access level."""
        if data.get("superuser"):
            self.create_superuser(data)
            return
        user = self.create_regular_user(data)
        self.apply_staff_flag(user, data)

    def create_superuser(self, data):
        """Create a superuser from fixture data."""
        self.User.objects.create_superuser(
            username=data["username"],
            email=data["email"],
            password=data["password"],
            first_name=data["first_name"],
            last_name=data["last_name"],
        )

    def create_regular_user(self, data):
        """Create a regular user from fixture data."""
        return self.User.objects.create_user(
            username=data["username"],
            email=data["email"],
            password=data["password"],
            first_name=data["first_name"],
            last_name=data["last_name"],
            bio=data.get("bio", ""),
        )

    def apply_staff_flag(self, user, data):
        """Apply staff flag if requested in fixture data."""
        if data.get("staff"):
            user.is_staff = True
            user.save()

    def create_departments(self):
        """Create standard departments (created_by picked from existing users)."""
        creator = self.get_first_user()
        if not creator:
            return
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
        if not self.users:
            return
        while Ticket.objects.count() < self.TICKET_COUNT:
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
        """Create between 1 and MAX_MESSAGES_PER_TICKET messages per ticket."""
        if not Ticket.objects.exists() or not self.users:
            return
        for ticket in Ticket.objects.all():
            self.create_messages_for_ticket(ticket)

    def create_messages_for_ticket(self, ticket):
        """Create messages for a ticket."""
        for _ in range(randint(1, self.MAX_MESSAGES_PER_TICKET)):
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
        if not self.departments:
            return
        for ticket in Ticket.objects.all():
            self.try_assign_ticket(ticket, choice(self.departments))

    def try_assign_ticket(self, ticket, department):
        """Attempt to create a TicketAssigned row; ignore errors (unique_together)."""
        try:
            TicketAssigned.objects.get_or_create(ticket=ticket, department=department)
        except Exception:
            pass

    def get_first_user(self):
        """Return the first available user, or None if no users exist."""
        return self.User.objects.first()