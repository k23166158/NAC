from django import forms
from django.contrib.auth import get_user_model

User = get_user_model()


class ForwardTicketForm(forms.Form):
    """Form to forward a ticket to another staff member."""
    email = forms.EmailField(
        label="Staff email",
        widget=forms.EmailInput(attrs={
            "placeholder": "teacher@school.edu",
            "autocomplete": "email",
        })
    )

    def clean_email(self):
        """Validate that the email belongs to a staff member."""
        email = self.cleaned_data["email"].strip().lower()
        try:
            user = User.objects.get(email__iexact=email)
        except User.DoesNotExist:
            raise forms.ValidationError("No user found with that email.")

        if not user.is_staff:
            raise forms.ValidationError("That user is not a staff member.")
        return email

    def get_user(self):
        """Retrieve the user instance based on the provided email."""
        email = self.cleaned_data["email"].strip().lower()
        return User.objects.get(email__iexact=email)
