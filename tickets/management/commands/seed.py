import hashlib
import json
import random
from pathlib import Path
from faker import Faker
from random import randint, choice, sample
from django.core.management.base import BaseCommand
from django.core.files.base import ContentFile
from tickets.models import *
from django.contrib.contenttypes.models import ContentType
from tickets.models.notification import Notification
from collections import defaultdict
from django.utils import timezone
from datetime import timedelta

SEED_DATA_FILENAME = "seed_data.json"
SEED_DATA_ATTRS = {
    "user_fixtures": "user_fixtures",
    "department_fixtures": "department_fixtures",
    "generic_department_faq_templates": "generic_department_faq_templates",
    "department_specific_faqs": "department_specific_faqs",
    "kcl_department_pool": "kcl_department_pool",
    "faq_tickets": "faq_tickets",
    "faq_responses": "faq_responses",
    "fallback_ticket_bodies": "fallback_ticket_bodies",
    "follow_up_responses": "follow_up_responses",
    "realistic_filenames": "realistic_filenames"
}

class Command(BaseCommand):
    """Build automation command to seed the database with data."""
    USER_COUNT = 100
    DEPARTMENT_COUNT = 30
    TICKET_COUNT = 200
    DEFAULT_PASSWORD = 'Password123'

    def __init__(self, *args, **kwargs):
        """Initialize the command with a locale-specific Faker instance."""
        super().__init__(*args, **kwargs)
        self.seed_data = self._load_seed_data()
        self._assign_seed_data()
        self.faq_bodies_by_title = {ticket["title"]: ticket["body"] for ticket in self.faq_tickets}
        self._seed_random_generators()

    def _assign_seed_data(self):
        """Assign JSON-backed seed collections onto the command instance."""
        for attr_name, data_key in SEED_DATA_ATTRS.items():
            setattr(self, attr_name, self.seed_data[data_key])

    def _seed_random_generators(self):
        """Initialise deterministic faker and random generators."""
        self.faker = Faker('en_GB')
        self.faker.seed_instance(1234)
        random.seed(1234)

    def _load_seed_data(self):
        """Return the static seeding payload loaded from JSON."""
        path = Path(__file__).with_name(SEED_DATA_FILENAME)
        with path.open(encoding="utf-8") as seed_file:
            return json.load(seed_file)

    def handle(self, *args, **options):
        """
        Runs the full seeding workflow and stores the data for any
        post-processing or debugging (not required for operation).
        """
        self.create_users()
        self.create_departments()
        self.assign_users_to_departments()
        self.create_department_faqs()
        self.create_tickets()
        self.assign_tickets_to_departments()
        self.create_ticket_messages()
        self.create_ticket_attachments()
        self.assign_staff_to_tickets()
        self.create_department_invitations()
        self.create_notifications()
    
    def create_users(self):
        """Create users in the database."""
        print("Creating users...")
        self.create_known_users()
        self.create_random_staff_users()
        self.create_random_users()
        print(f"{User.objects.count()} Users created.")

    def create_known_users(self):
        """Create users from predefined fixtures."""
        for fixture in self.user_fixtures:
            self._seed_user(
                username=fixture['username'],
                password=self.DEFAULT_PASSWORD,
                **self._known_user_defaults(fixture),
            )

    def _known_user_defaults(self, fixture):
        """Return update defaults for a fixture-backed user."""
        return {
            'email': fixture['email'],
            'first_name': fixture['first_name'],
            'last_name': fixture['last_name'],
            'is_superuser': fixture.get('superuser', False),
            'is_staff': fixture.get('staff', False),
        }

    def _set_seed_password(self, user, password):
        """Ensure a seeded user has the default password."""
        user.set_password(password)
        user.save(update_fields=['password'])

    def _seed_user(self, *, username, password, **defaults):
        """Create or update one seeded user and apply seed assets."""
        user, _created = User.objects.update_or_create(
            username=username,
            defaults=defaults,
        )
        self._set_seed_password(user, password)
        self._set_seed_profile_picture(user)
        return user

    def _set_seed_profile_picture(self, user):
        """Attach a deterministic seeded profile picture to a user."""
        if user.profile_picture:
            user.profile_picture.delete(save=False)
        user.profile_picture.save(
            self._profile_picture_filename(user),
            ContentFile(self._profile_picture_svg(user)),
            save=False,
        )
        user.save(update_fields=['profile_picture'])

    def _profile_picture_filename(self, user):
        """Return the storage filename for a seeded profile picture."""
        return f"seed-{user.username}.svg"

    def _profile_picture_svg(self, user):
        """Build a simple SVG avatar using deterministic initials and colour."""
        initials = self._profile_picture_initials(user)
        color = self._profile_picture_color(user.username)
        svg = (
            "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 128 128'>"
            f"<rect width='128' height='128' rx='24' fill='{color}'/>"
            f"<text x='50%' y='50%' text-anchor='middle' dominant-baseline='middle' fill='white' "
            "font-family='Arial, sans-serif' font-size='44' font-weight='700'>"
            f"{initials}</text></svg>"
        )
        return svg.encode("utf-8")

    def _profile_picture_initials(self, user):
        """Return initials for seeded profile pictures."""
        letters = f"{user.first_name[:1]}{user.last_name[:1]}".strip()
        return (letters or user.username[:2]).upper()

    def _profile_picture_color(self, seed_text):
        """Return a deterministic avatar background colour."""
        return f"#{hashlib.md5(seed_text.encode()).hexdigest()[:6]}"

    def create_random_staff_users(self):
        """Create random staff users using Faker library."""
        for _ in range((self.USER_COUNT - len(self.user_fixtures)) // 2):
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
        for _ in range((self.USER_COUNT - len(self.user_fixtures)) // 2):
            first_name = self.faker.first_name()
            last_name = self.faker.last_name()
            username = f"@{first_name.lower()}{last_name.lower()}{randint(1, 9999)}"
            email = f"{username}@example.org"

            self.try_create_user(
                username=username, email=email, password=self.DEFAULT_PASSWORD,
                first_name=first_name, last_name=last_name,
            )

    def try_create_user(self, **kwargs):
        """Attempt to create a user, handling any errors."""
        try:
            password = kwargs.pop("password")
            self._seed_user(password=password, **kwargs)
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
        for fixture in self.department_fixtures:
            creator = User.objects.get(username=fixture['created_by'])
            Department.objects.update_or_create(
                name=fixture['name'],
                defaults={
                    'description': fixture.get('description', ''),
                    'created_by': creator,
                },
            )

    def create_random_departments(self):
        """Create university-style department names and descriptions."""
        staff = list(User.objects.filter(is_staff=True))
        existing_names = {dept.name for dept in Department.objects.all()}
        available_names = [name for name in self.kcl_department_pool if name not in existing_names]
        for index in range(self.DEPARTMENT_COUNT - len(self.department_fixtures)):
            name = self._department_name_for_index(index, available_names)
            Department.objects.get_or_create(name=name, defaults=self._random_department_defaults(staff))
            existing_names.add(name)

    def _random_department_defaults(self, staff):
        """Return defaults for a random seeded department."""
        return {
            'description': (
                "Provides support for students and staff with administrative and academic service requests."
            ),
            'created_by': choice(staff),
        }

    def _department_name_for_index(self, index, available_names):
        """Return the most suitable seeded department name for an index."""
        if index < len(available_names):
            return available_names[index]
        return self._next_fallback_department_name()

    def _next_fallback_department_name(self):
        """Return the next available fallback department name."""
        number = 1
        while Department.objects.filter(name=f"Student Services Unit {number}").exists():
            number += 1
        return f"Student Services Unit {number}"

    def try_create_department(self, **kwargs):
        """Attempt to create a department, handling any errors."""
        try:
            Department.objects.create(**kwargs)
        except Exception:
            pass

    def create_department_faqs(self):
        """Create university-style FAQs for every seeded department."""
        print("Creating department FAQs...")
        created = sum(
            self._create_faqs_for_department(department)
            for department in Department.objects.all().order_by("name")
        )
        print(f"{created} Department FAQs created.")

    def _faq_entries_for_department(self, department):
        """Return generic and department-specific FAQ entries for a department."""
        formatted_generic_entries = [
            {
                "question": template["question"].format(department=department.name),
                "answer": template["answer"].format(department=department.name),
            }
            for template in self.generic_department_faq_templates
        ]
        return formatted_generic_entries + self.department_specific_faqs.get(department.name, [])

    def _create_faqs_for_department(self, department):
        """Create FAQ entries for one department and return how many were added."""
        created = 0
        for order, faq in enumerate(self._faq_entries_for_department(department)):
            created += self._create_department_faq(department, faq, order)
        return created

    def _create_department_faq(self, department, faq, order):
        """Create one department FAQ if it does not already exist."""
        _, was_created = DepartmentFAQ.objects.get_or_create(
            department=department,
            question=faq["question"],
            defaults=self._department_faq_defaults(department, faq, order),
        )
        return int(was_created)

    def _department_faq_defaults(self, department, faq, order):
        """Return default values for a seeded department FAQ."""
        return {
            "answer": faq["answer"],
            "created_by": department.created_by,
            "order": order,
        }

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
        """Create tickets in the database using FAQ-style content."""
        print("Creating tickets...")
        users = list(User.objects.all())
        self._seed_fixture_user_tickets()
        self._create_seeded_faq_tickets(users)
        self._create_remaining_tickets(users)
        print(f"{Ticket.objects.count()} Tickets created.")

    def _seed_fixture_user_tickets(self):
        """Ensure all fixture users have a minimum number of personal tickets."""
        fixture_usernames = [f['username'] for f in self.user_fixtures]
        fixture_users = User.objects.filter(username__in=fixture_usernames)

        for user in fixture_users:
            num_tickets = randint(60, 80)
            self._create_num_tickets(num_tickets, user)

    def _create_num_tickets(self, num_tickets, user):
        """Create num_tickets tickets for the user"""
        for _ in range(num_tickets):
            self._create_ticket_with_title(choice(self.faq_tickets)['title'], user)

    def _create_seeded_faq_tickets(self, users):
        """Create one ticket per FAQ entry."""
        for faq in self.faq_tickets:
            self._create_ticket_with_title(faq['title'], choice(users))

    def _create_remaining_tickets(self, users):
        """Fill up ticket count using FAQ-style titles."""
        current_count = Ticket.objects.count()
        remaining = self.TICKET_COUNT - current_count
        
        for _ in range(max(0, remaining)):
            self._create_ticket_with_title(choice(self.faq_tickets)['title'], choice(users))

    def _create_ticket_with_title(self, title, creator):
        """Create a single ticket with a realistic title and random date."""
        ticket = Ticket.objects.create(title=title, status=choice(['open', 'closed']), created_by=creator)
        random_days, random_seconds = randint(2, 10), randint(0, 86400)
        past_date = timezone.now() - timedelta(days=random_days, seconds=random_seconds)
        Ticket.objects.filter(id=ticket.id).update(created_at=past_date, updated_at=past_date)
        return ticket

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
        """Create ticket messages in the database using FAQ-style responses."""
        print("Creating ticket messages...")
        for ticket in Ticket.objects.all():
            self._create_initial_message_for_ticket(ticket)
            self.create_ticket_response_messages(ticket)
        print("Ticket messages created.")

    def _create_initial_message_for_ticket(self, ticket):
        """Create the initial message for a single ticket."""
        initial_body = self.faq_bodies_by_title.get(ticket.title, choice(self.fallback_ticket_bodies))
        past_date = timezone.now() - timedelta(days=randint(2, 10), seconds=randint(0, 86400))
        msg = TicketMessage.objects.get_or_create(
            ticket=ticket, body=initial_body, sender=ticket.created_by
        )[0]
        TicketMessage.objects.filter(id=msg.id).update(created_at=past_date, edited_at=past_date)
    
    def create_ticket_response_messages(self, ticket):
        """Create response messages from staff using FAQ-style responses."""
        num_messages = randint(2, 4)
        for _ in range(num_messages):
            available_senders = list(User.objects.filter(
                is_staff=True, 
                user__department__assigned_tickets__ticket=ticket
            ).distinct())

            self.create_staff_ticket_response_messages(ticket, available_senders)
            self.random_create_user_ticket_response_messages(ticket)

    def create_staff_ticket_response_messages(self, ticket, available_senders):
        """Create response messages from staff for a ticket using FAQ responses."""
        if available_senders:
            sender = choice(available_senders)
            body = choice(self.faq_responses)
            msg = TicketMessage.objects.create(ticket=ticket, sender=sender, body=body)
            past_date = timezone.now() - timedelta(days=randint(2, 10), seconds=randint(0, 86400))

            TicketMessage.objects.filter(id=msg.id).update(
                created_at=past_date,
                edited_at=past_date
            )
    
    def random_create_user_ticket_response_messages(self, ticket):
        """Randomly create follow-up messages from users for a ticket."""
        if randint(0, 1):
            sender = ticket.created_by
            body = choice(self.follow_up_responses)
            msg = TicketMessage.objects.create(ticket=ticket, sender=sender, body=body)
            past_date = timezone.now() - timedelta(days=randint(2, 10), seconds=randint(0, 86400))

            TicketMessage.objects.filter(id=msg.id).update(
                created_at=past_date,
                edited_at=past_date
            )

    def _create_single_attachment(self, message):
        """Create one attachment for a message with realistic document names."""
        filename = choice(self.realistic_filenames)
        content = self._attachment_content(filename)
        file_content = ContentFile(content.encode(), name=filename)
        TicketMessageAttachment.objects.create(
            ticket=message.ticket,
            message=message,
            file=file_content,
            original_name=filename,
            content_type=self._attachment_content_type(filename),
            size_bytes=len(content.encode()),
            uploaded_by=message.sender or message.ticket.created_by,
        )

    def _attachment_content(self, filename):
        """Create deterministic readable content for an attached file."""
        return (
            f"{filename}\n\n"
            "This supporting document was uploaded with the ticket to provide relevant evidence "
            "for review by the assigned department."
        )

    def _attachment_content_type(self, filename):
        """Return a basic content type based on file extension."""
        if filename.endswith('.pdf'):
            return "application/pdf"
        return "text/plain"

    def _create_message_attachments(self, message):
        """Create random attachments for a single message."""
        if randint(0, 100) >= 30:
            return 0
        count = randint(1, 3)
        for _ in range(count):
            self._create_single_attachment(message)
        return count

    def create_ticket_attachments(self):
        """Create random attachments for ticket messages."""
        print("Creating ticket attachments...")
        total = sum(self._create_message_attachments(m) for m in TicketMessage.objects.all())
        print(f"{total} Attachments created.")

    def assign_staff_to_tickets(self):
        """Randomly assign staff members as participants to tickets."""
        print("Assigning staff to tickets...")
        tickets = list(Ticket.objects.all())
        staff_users = list(User.objects.filter(is_staff=True))

        for ticket in tickets:
            num_participants = randint(1, 3)
            participants = random.sample(staff_users, num_participants)
            self.add_participants_to_ticket(ticket, participants)

        print("Staff assignments to tickets complete.")

    def add_participants_to_ticket(self, ticket, participants):
        """Assign multiple staff members as participants to a ticket."""
        for user in participants:
            TicketParticipant.objects.get_or_create(ticket=ticket, user=user)

    def _create_invites_for_staff(self, staff, departments):
        """Create 1-3 pending department invites for one staff user."""
        staff_dept_ids = set(
            UserDepartments.objects.filter(user=staff).values_list('department_id', flat=True)
        )
        available = [d for d in departments if d.id not in staff_dept_ids]
        num_invitations = min(randint(1, 3), len(available))
        if num_invitations == 0:
            return
        for department in random.sample(available, num_invitations):
            DepartmentInvitation.objects.get_or_create(
                department=department,
                recipient=staff,
                status='pending',
                defaults={'sender': department.created_by},
            )

    def create_department_invitations(self):
        """Creates a random amount of department invitations between 1 and 3 for staff users."""
        print("Creating department invitations...")
        staff_users = list(User.objects.filter(is_staff=True))
        departments = list(Department.objects.all())
        for staff in staff_users:
            self._create_invites_for_staff(staff, departments)
        print("Department invitations created.")

    def create_notifications(self):
        """Create many realistic notifications for tickets."""
        users, tickets = list(User.objects.all()), list(Ticket.objects.all())
        ct = ContentType.objects.get_for_model(Ticket)
        stats = defaultdict(int)

        total = self._process_initial_tickets(users, tickets, ct, stats)
        total += self._ensure_min_notifs(users, tickets, ct, stats)

        print(f"{total} Notifications created.")

    def _process_initial_tickets(self, users, tickets, ct, stats):
        """Processes the initial wave of ticket notifications."""
        created = 0
        for ticket in tickets:
            created += self._create_multiple_notifs(ticket, users, ct, stats)
        return created

    def _create_multiple_notifs(self, ticket, users, ct, stats):
        """Generates 2 to 6 notifications per ticket."""
        if len(users) < 2: return 0
        
        count = randint(2, 6)
        for _ in range(count):
            actor, recipient = sample(users, 2)
            self._save_notif(actor, recipient, ticket, ct, choice([True, False]))
            stats[actor.id] += 1
        return count

    def _ensure_min_notifs(self, users, tickets, ct, stats):
        """Ensures every user is an actor at least 5 times."""
        created = 0
        for actor in users:
            created += self._fill_quota(actor, users, tickets, ct, stats)
        return created

    def _fill_quota(self, actor, users, tickets, ct, stats):
        """Creates missing notifications for a specific actor."""
        required = max(0, 5 - stats[actor.id])
        for _ in range(required):
            recipient = self._get_random_other(actor, users)
            self._save_notif(actor, recipient, choice(tickets), ct, False)
        return required

    def _get_random_other(self, actor, users):
        """Gets a random user that is not the specified actor."""
        others = [u for u in users if u != actor]
        return choice(others) if others else actor

    def _save_notif(self, actor, recipient, ticket, ct, is_read):
        """Saves a Notification instance to the database."""
        msg = (
            f"{actor.get_full_name() or actor.username} performed an action "
            f"related to the ticket \"{ticket.title}\".\n\n"
            f"You are receiving this notification because you are involved "
            f"in the ticket or were recently added to it."
        )
        Notification.objects.create(
            user=recipient, actor=actor, content_type=ct, object_id=ticket.id,
            notification_type=Notification.NotificationType.TICKET_CREATED,
            short_message=f"{actor.username} interacted with ticket: {ticket.title}",
            is_read=is_read
        )
