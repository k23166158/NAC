from django.http import JsonResponse
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from tickets.models import Department

User = get_user_model()

@login_required
def search_assignables(request):
    """View to search for assignable staff and departments based on a query parameter 'q'."""
    q = request.GET.get("q", "").strip()

    staff, departments = get_assignables(q, User, Department)
    results = (
        format_staff_results(staff)
        + format_department_results(departments)
    )

    return JsonResponse(results, safe=False)


def get_assignables(q, User, Department):
    """Helper function to get assignable staff and departments based on a search query."""
    staff = User.objects.filter(
        is_staff=True,
        username__icontains=q,
    )[:5]

    departments = Department.objects.filter(
        name__icontains=q,
    )[:5]

    return staff, departments


def format_staff_results(staff):
    """Format staff user results for the search assignables endpoint."""
    return [
        {
            "id": u.id,
            "type": "staff",
            "label": f"{u.get_full_name()} (@{u.username})",
        }
        for u in staff
    ]


def format_department_results(departments):
    """Get department results formatted for the search assignables endpoint."""
    return [
        {
            "id": d.id,
            "type": "department",
            "label": f"{d.name} (Department)",
        }
        for d in departments
    ]
