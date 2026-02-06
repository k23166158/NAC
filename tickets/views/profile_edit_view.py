from django.contrib.auth.views import redirect_to_login
from django.contrib.auth import update_session_auth_hash
from django.db import IntegrityError
from django.shortcuts import redirect, render
from django.views import View


class ProfileEditView(View):
    """Allow an authenticated user to edit their own profile details."""

    template_name = "profile_edit.html"

    def get(self, request):
        """Render the edit profile page for the current user."""
        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path())
        return render(request, self.template_name, {"user": request.user})

    def post(self, request):
        """Update the current user's profile and redirect back to profile."""
        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path())

        user, password_changed = self._apply_updates(request)
        response = self._try_save_user(request, user)
        if response is not None:
            return response

        if password_changed:
            update_session_auth_hash(request, user)
        return redirect("my_profile")

    def _apply_updates(self, request):
        """Apply form values and uploaded file to the given user instance."""
        user = request.user
        self._set_basic_fields(user, request)
        self._set_profile_picture(user, request)
        password_changed = self._set_password_if_provided(user, request)
        return user, password_changed

    def _set_basic_fields(self, user, request):
        """Populate basic user fields from POST data."""
        user.first_name = request.POST.get("first_name", "").strip()
        user.last_name = request.POST.get("last_name", "").strip()
        user.username = request.POST.get("username", "").strip()
        user.email = request.POST.get("email", "").lower().strip()

    def _set_profile_picture(self, user, request):
        """Attach a newly uploaded profile picture to the user, if present."""
        upload = request.FILES.get("profile_picture")
        if upload is not None:
            user.profile_picture = upload

    def _set_password_if_provided(self, user, request):
        """Set a new password if provided; returns True if changed."""
        password = request.POST.get("password", "").strip()
        if not password:
            return False
        user.set_password(password)
        return True

    def _try_save_user(self, request, user):
        """Save the user; return an error response if uniqueness fails."""
        try:
            user.save()
            return None
        except IntegrityError:
            return render(
                request,
                self.template_name,
                {"user": user, "error": "Email or username already exists."},
            )
