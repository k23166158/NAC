from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.views import redirect_to_login
from django.db import IntegrityError, transaction
from django.shortcuts import redirect, render
from django.views import View


class ProfileEditView(View):
    """Allow an authenticated user to edit their own profile details."""

    template_name = "profile_edit.html"

    def get(self, request):
        """Render the profile edit form for authenticated users."""
        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path())
        return render(request, self.template_name, {"user": request.user})

    def post(self, request):
        """Process profile update submissions."""
        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path())
    
        user = request.user
        pwd_changed = self._apply_profile_updates(request, user)
        
        if not self._is_save_successful(user):
            return self._render_duplicate_error(request, user)
        if pwd_changed:
            update_session_auth_hash(request, user)

        return redirect("profile", profile_slug=user.profile_slug)

    def _is_save_successful(self, user):
        """Wraps the atomic save in a try-except to flatten nesting."""
        try:
            return self._execute_atomic_save(user)
        except IntegrityError:
            return False

    def _execute_atomic_save(self, user):
        """Performs the actual atomic save."""
        with transaction.atomic():
            user.save()
        return True

    def _apply_profile_updates(self, request, user):
        """Update profile fields and password, returns if password changed."""
        user.first_name = request.POST.get("first_name", "").strip()
        user.last_name = request.POST.get("last_name", "").strip()
        user.username = request.POST.get("username", "").strip()
        user.email = request.POST.get("email", "").lower().strip()
        
        self._handle_file_upload(request, user)
        return self._handle_password_update(request, user)

    def _handle_file_upload(self, request, user):
        """Handles the profile picture if it exists in the request."""
        if "profile_picture" in request.FILES:
            user.profile_picture = request.FILES["profile_picture"]

    def _handle_password_update(self, request, user):
        """Updates password if provided and returns change status."""
        password = request.POST.get("password", "").strip()
        if not password:
            return False
        user.set_password(password)
        return True

    def _render_duplicate_error(self, request, user):
        """Render the form with a duplicate username/email error."""
        return render(
            request,
            self.template_name,
            {
                "user": user,
                "error": "Email or username already exists.",
            },
        )