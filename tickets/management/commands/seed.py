import random
from faker import Faker
from random import randint, choice
from django.core.management.base import BaseCommand
from tickets.models import *

user_fixtures = [
    {'username': 'johndoe', 'email': 'johndoe@example.org', 'first_name': 'John', 'last_name': 'Doe', 'superuser' : True, 'staff': True},
    {'username': 'janedoe', 'email': 'janedoe@example.org', 'first_name': 'Jane', 'last_name': 'Doe', 'staff': True},
    {'username': 'charlie', 'email': 'charliejohnson@example.org', 'first_name': 'Charlie', 'last_name': 'Johnson'},
]

department_fixtures = [
    {'name': 'Informatics', 'description': 'Handles all issues related to Informatics', 'created_by': '@janedoe'},
]

class Command(BaseCommand):
    """Build automation command to seed the database with data."""
    USER_COUNT = 100
    DEPARTMENT_COUNT = 30
    TICKET_COUNT = 200
    DEFAULT_PASSWORD = 'Password123'

    def __init__(self, *args, **kwargs):
        """Initialize the command with a locale-specific Faker instance."""
        super().__init__(*args, **kwargs)
        self.faker = Faker('en_GB')
        self.faker.seed_instance(1234)
        random.seed(1234)

    def handle(self, *args, **options):
        """
        Django entrypoint for the command.

        Runs the full seeding workflow and stores the data for any
        post-processing or debugging (not required for operation).
        """
        self.create_users()
        self.create_departments()
        self.assign_users_to_departments()
        self.create_tickets()
        self.assign_tickets_to_departments()
        self.create_ticket_messages()
    
    def create_users(self):
        """Create users in the database."""
        print("Creating users...")
        self.create_known_users()
        self.create_random_staff_users()
        self.create_random_users()
        print(f"{User.objects.count()} Users created.")

    def create_known_users(self):
        """Create users from predefined fixtures."""
        for fixture in user_fixtures: 
            User.objects.create_user(
                username=fixture['username'], email=fixture['email'], password=self.DEFAULT_PASSWORD,
                first_name=fixture['first_name'], last_name=fixture['last_name'],
                is_superuser=fixture.get('superuser', False), is_staff=fixture.get('staff', False)
            )

    def create_random_staff_users(self):
        """Create random staff users using Faker library."""
        for _ in range((self.USER_COUNT - len(user_fixtures)) // 2):
            first_name = self.faker.first_name()
            last_name = self.faker.last_name()
            username = f"{first_name.lower()}{last_name.lower()}{randint(1, 9999)}"
            email = f"{username}@example.org"

            self.try_create_user(
                username=username, email=email, password=self.DEFAULT_PASSWORD, 
                first_name=first_name, last_name=last_name, is_staff=True,
            )

    def create_random_users(self):
        """Create random users using Faker library."""
        for _ in range((self.USER_COUNT - len(user_fixtures)) // 2):
            first_name = self.faker.first_name()
            last_name = self.faker.last_name()
            username = f"@{first_name.lower()}{last_name.lower()}{randint(1, 9999)}"
            email = f"{first_name.lower()}.{last_name.lower()}{randint(1, 9999)}@example.org"

            self.try_create_user(
                username=username, email=email, password=self.DEFAULT_PASSWORD,
                first_name=first_name, last_name=last_name,
            )

    def try_create_user(self, **kwargs):
        """Attempt to create a user, handling any errors."""
        try:
            User.objects.create_user(**kwargs)
        except Exception:
            pass

    def create_departments(self):
        """Create departments in the database."""
        print("Creating departments...")
        self.create_known_departments()
        self.create_random_departments()
        print(f"{Department.objects.count()} Departments created.")

    def create_known_departments(self):
        """Create departments from predefined fixtures."""
        for fixture in department_fixtures:
            creator = User.objects.get(username=fixture['created_by'])
            Department.objects.create(
                name=fixture['name'],
                description=fixture.get('description', ''),
                created_by=creator
            )

    def create_random_departments(self):
        """Create random departments using Faker library."""
        staff = list(User.objects.filter(is_staff=True))
        for _ in range(self.DEPARTMENT_COUNT - len(department_fixtures)):
            name = self.faker.unique.company()
            description = self.faker.text(max_nb_chars=200)
            created_by = choice(staff)

            Department.objects.create(name=name, description=description, created_by=created_by)

    def try_create_department(self, **kwargs):
        """Attempt to create a department, handling any errors."""
        try:
            Department.objects.create(**kwargs)
        except Exception:
            pass

    def assign_users_to_departments(self):
        """Randomly assign users to departments."""
        print("Assigning users to departments...")
        users = list(User.objects.filter(is_staff=True))
        departments = list(Department.objects.all())
        
        for department in departments:
            UserDepartments.objects.get_or_create(user=department.created_by, department=department)
            num_assignments = randint(5, 10)
            assigned_users = random.sample(users, num_assignments)
            self.add_users_to_department(assigned_users, department)

        print("User assignments complete.")

    def add_users_to_department(self, users, department):
        """Assign multiple users to a department."""
        for user in users:
            UserDepartments.objects.get_or_create(user=user, department=department)

    def create_tickets(self):
        """Create tickets in the database."""
        print("Creating tickets...")
        users = list(User.objects.all())
        for _ in range(self.TICKET_COUNT):
            title = self.faker.sentence(nb_words=6)
            status = choice(['open', 'closed'])
            created_by = choice(users)
            Ticket.objects.create(title=title, status=status, created_by=created_by)

        print(f"{Ticket.objects.count()} Tickets created.")

    def assign_tickets_to_departments(self):
        """Randomly assign tickets to departments."""
        print("Assigning tickets to departments...")

        tickets = list(Ticket.objects.all())
        departments = list(Department.objects.all())

        for ticket in tickets:
            num_assignments = randint(1, 3)
            available_departments = random.sample(departments, num_assignments)
            self.add_tickets_to_department(ticket, available_departments)

        print("Ticket assignments complete.")

    def add_tickets_to_department(self, ticket, departments):
        """Assign multiple tickets to multiple departments."""
        for department in departments:
            TicketAssigned.objects.get_or_create(ticket=ticket, department=department)

    def create_ticket_messages(self):
        """Create ticket messages in the database."""
        print("Creating ticket messages...")
        tickets = list(Ticket.objects.all())
        
        for ticket in tickets:
            TicketMessage.objects.get_or_create(
                ticket=ticket,
                body=self.faker.paragraph(nb_sentences=3),
                sender=ticket.created_by,
            )
            self.create_ticket_response_messages(ticket)

        print("Ticket messages created.")
    
    def create_ticket_response_messages(self, ticket):
        """Create initial response messages from staff for a ticket."""

        num_messages = randint(4, 6)
        for _ in range(num_messages):

            available_senders = list(User.objects.filter(
                is_staff=True, 
                user__department__assigned_tickets__ticket=ticket
            ).distinct())

            self.create_staff_ticket_response_messages(ticket, available_senders)
            self.random_create_user_ticket_response_messages(ticket)

    def create_staff_ticket_response_messages(self, ticket, available_senders):
        """Create response messages from staff for a ticket."""
        if available_senders:
            sender = choice(available_senders)
            body = self.faker.paragraph(nb_sentences=3)
            TicketMessage.objects.create(ticket=ticket, sender=sender, body=body)
    
    def random_create_user_ticket_response_messages(self, ticket):
        """Randomly create response messages from users for a ticket."""
        if randint(0, 1):
            sender = ticket.created_by
            body = self.faker.paragraph(nb_sentences=3)
            TicketMessage.objects.create(ticket=ticket, sender=sender, body=body)