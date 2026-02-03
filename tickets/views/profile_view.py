from django.contrib.auth.views import redirect_to_login
from django.shortcuts import get_object_or_404, render, redirect
from django.views import View
from tickets.models import User


class ProfileView(View):
    """Displays another user's profile."""
    def get(self, request, pk):
        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path())

        if request.user.pk == pk:
            return redirect("my_profile")

        user_obj = get_object_or_404(User, pk=pk)

        return render(
            request,
            "profile.html",
            {
                "profile_user": user_obj,
                "is_own_profile": False,
            },
        )
