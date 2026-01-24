from django.contrib.auth import get_user_model
from django.db import transaction

from tickets.models import Department

def _get_or_create_seed_user():
    """
    Creates (or returns) a seed user to attach ownership fields to.
    This user is only for seeding purposes and should not be used in production.
    """
    User = get_user_model()

    username = "seed_admin"
    email = "seed_admin@example.com"

    user, created = User.objects.get_or_create(
        username=username,
        defaults={
            "email": email,
            "first_name": "Seed",
            "last_name": "Admin",
        },
    )

    if created:
        user.set_password("seedpass123") 
        user.save()

    return user


def seed_departments():
    """
    Seed default Department rows.
    Uses get_or_create so it won't duplicate departments on repeated runs.
    """
    seed_user = _get_or_create_seed_user()

    default_departments = [
        "NMES",
        "Finance",
        "HR",
        "Support",
        "Art and Humanities",
        "Classics",
    ]

    created_count = 0
    for name in default_departments:
        _, created = Department.objects.get_or_create(
            name=name,
            defaults={"created_by": seed_user},
        )
        created_count += int(created)

    return {
        "departments_created": created_count,
        "departments_total": Department.objects.count(),
    }


# Add new seed functions above this 

# Add any new seed functions here, e.g. seed_tickets, seed_categories, etc.
SEED_FUNCTIONS = [
    seed_departments,
]

@transaction.atomic
def run_seeds():
    """
    Run all seed functions inside a single DB transaction.
    If anything fails, nothing is partially inserted.
    """
    results = []
    for seed in SEED_FUNCTIONS:
        results.append({seed.__name__: seed()})
    return results