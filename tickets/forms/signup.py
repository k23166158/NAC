from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm

User = get_user_model()

class SignUpForm(UserCreationForm):
    """User sign-up form with custom fields and validation for the Student Support System."""
    class Meta(UserCreationForm.Meta):
        """Metadata for SignUpForm specifying model and fields to include in the form."""
        model = User
        fields = ("username", "first_name", "last_name", "email", "profile_picture", "bio")

    def clean_email(self):
        """Validate that the email is unique (case-insensitive) and return the cleaned value."""
        email = self.cleaned_data["email"].lower().strip()
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("This email is already in use.")
        return email

    def create_active_user(self):
        """Create and return a standard active non-staff user from valid form data."""
        user = self.save(commit=False)
        user.is_superuser = False
        user.is_staff = False
        user.is_active = True
        user.email = user.email.lower().strip()
        user.save()
        return user
