from django.http import JsonResponse
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from tickets.models import Department

User = get_user_model()


@login_required
def search_assignables(request):
    """
    Search staff users and departments for ticket assignment.
    Used via AJAX from the ticket thread page.
    """
    q = request.GET.get("q", "").strip()

    staff = User.objects.filter(
        is_staff=True,
        username__icontains=q,
    )[:5]

    departments = Department.objects.filter(
        name__icontains=q,
    )[:5]

    results = []

    for user in staff:
        results.append({
            "id": user.id,
            "type": "staff",
            "label": f"{user.get_full_name()} (@{user.username})",
        })

    for dept in departments:
        results.append({
            "id": dept.id,
            "type": "department",
            "label": f"{dept.name} (Department)",
        })

    return JsonResponse(results, safe=False)
