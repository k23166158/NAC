from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.views import redirect_to_login
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
        pwd_changed = user.apply_profile_changes(request.POST, request.FILES)
        
        if not user.save_profile_changes():
            return self._render_duplicate_error(request, user)
        if pwd_changed:
            update_session_auth_hash(request, user)

        return redirect("profile", profile_slug=user.profile_slug)

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
