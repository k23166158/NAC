from django.contrib.auth.views import redirect_to_login
from django.shortcuts import render
from django.views import View


class MyProfileView(View):
    """Displays the logged-in user's profile."""

    def get(self, request):
        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path())

        return render(
            request,
            "profile.html",
            {
                "profile_user": request.user,
                "is_own_profile": True,
            },
        )
