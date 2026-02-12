from django.contrib.auth.views import redirect_to_login
from django.shortcuts import get_object_or_404, render
from django.views import View
from tickets.models import User


class ProfileView(View):
    """Displays a user's profile by profile_slug."""
    def get(self, request, profile_slug):
        """Render profile page for the given profile_slug."""
        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path())

        profile_user = get_object_or_404(User, profile_slug=profile_slug)
        return render(
            request,
            "profile.html",
            {
                "profile_user": profile_user,
                "is_own_profile": request.user.pk == profile_user.pk,
            },
        )