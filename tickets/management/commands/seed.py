from django.contrib.auth import get_user_model
from django.db import transaction
from tickets.models import Department
from django.core.management.base import BaseCommand

SEED_USERNAME = "seed_admin"
SEED_EMAIL = "seed_admin@example.com"
SEED_PASSWORD = "seedpass123"

DEFAULT_DEPARTMENTS = [
    "NMES",
    "Finance",
    "HR",
    "Support",
    "Art and Humanities",
    "Classics",
]

class Command(BaseCommand):
    """Django management command to seed the database with initial data."""
    help = "Seed the database with initial data."

    def handle(self, *args, **options):
        """Handle the command execution."""
        results = run_seeds()
        self.stdout.write(self.style.SUCCESS(f"Seeding complete: {results}"))

def _seed_user_defaults():
    """Default fields used when creating the seed user."""
    return {"email": SEED_EMAIL, "first_name": "Seed", "last_name": "Admin"}

def _get_or_create_seed_user():
    """
    Creates (or returns) a seed user to attach ownership fields to.
    This user is only for seeding purposes and should not be used in production.
    """
    User = get_user_model()
    user, created = User.objects.get_or_create(
        username=SEED_USERNAME, defaults=_seed_user_defaults()
    )
    if created:
        user.set_password(SEED_PASSWORD)
        user.save()
    return user

def _get_or_create_department(name, seed_user):
    """
    Get or create a Department with the given name.
    Uses get_or_create so repeated seed runs do not create duplicates.
    """
    return Department.objects.get_or_create(
        name=name,
        defaults={"created_by": seed_user},
    )

def seed_departments():
    """
    Seed default Department rows.
    Uses get_or_create so it won't duplicate departments on repeated runs.
    """
    seed_user = _get_or_create_seed_user()
    created_count = 0
    for name in DEFAULT_DEPARTMENTS:
        _, created = _get_or_create_department(name, seed_user)
        created_count += int(created)
    return {"departments_created": created_count, "departments_total": Department.objects.count()}


# Add new seed functions above this


# Add any new seed functions here, e.g. seed_tickets, seed_categories, etc.
SEED_FUNCTIONS = [
    seed_departments,
]


@transaction.atomic
def run_seeds():
    """
    Run all seed functions inside a single DB transaction.
    If anything fails nothing is partially inserted.
    """
    results = []
    for seed in SEED_FUNCTIONS:
        results.append({seed.__name__: seed()})
    return results