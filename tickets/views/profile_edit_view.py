from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.views import redirect_to_login
from django.db import IntegrityError
from django.shortcuts import redirect, render
from django.views import View


class ProfileEditView(View):
    """Allow an authenticated user to edit their own profile details."""

    template_name = "profile_edit.html"

    def get(self, request):
        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path())
        return render(request, self.template_name, {"user": request.user})

    def post(self, request):
        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path())

        user = request.user
        password_changed = False
        user.first_name = request.POST.get("first_name", "").strip()
        user.last_name = request.POST.get("last_name", "").strip()
        user.username = request.POST.get("username", "").strip()
        user.email = request.POST.get("email", "").lower().strip()

        if "profile_picture" in request.FILES:
            user.profile_picture = request.FILES["profile_picture"]
        password = request.POST.get("password", "").strip()
        if password:
            user.set_password(password)
            password_changed = True
        try:
            user.save()
        except IntegrityError:
            return render(
                request,
                self.template_name,
                {
                    "user": user,
                    "error": "Email or username already exists.",
                },
            )
        if password_changed:
            update_session_auth_hash(request, user)
        return redirect("profile", profile_slug=user.profile_slug)