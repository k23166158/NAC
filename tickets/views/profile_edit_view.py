from django.contrib.auth.views import redirect_to_login
from django.contrib.auth import update_session_auth_hash
from django.shortcuts import redirect, render
from django.views import View
from django.db import IntegrityError


class ProfileEditView(View):
    """Allows the logged-in user to edit their profile."""

    def get(self, request):
        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path())
        return render(request, "profile_edit.html", {"user": request.user})

    def post(self, request):
        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path())

        user = request.user
        user.first_name = request.POST.get("first_name", "").strip()
        user.last_name = request.POST.get("last_name", "").strip()
        user.username = request.POST.get("username", "").strip()
        user.email = request.POST.get("email", "").lower().strip()

        if "profile_picture" in request.FILES:
            user.profile_picture = request.FILES["profile_picture"]

        password = request.POST.get("password", "").strip()
        if password:
            user.set_password(password)

        try:
            user.save()
        except IntegrityError:
            return render(
                request,
                "profile_edit.html",
                {"user": user, "error": "Email or username already exists."},
            )

        if password:
            update_session_auth_hash(request, user)

        return redirect("my_profile")
