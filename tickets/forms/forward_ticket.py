from django import forms
from django.contrib.auth import get_user_model

User = get_user_model()

class ForwardTicketForm(forms.Form):
    email = forms.EmailField(label="Staff email", widget=forms.EmailInput(attrs={
        "placeholder": "teacher@school.edu"
    }))

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        try:
            user = User.objects.get(email__iexact=email)
        except User.DoesNotExist:
            raise forms.ValidationError("No user found with that email.")

        if not user.is_staff:
            raise forms.ValidationError("That user is not a staff member.")
        return email

    def get_user(self):
        email = self.cleaned_data["email"].strip().lower()
        return User.objects.get(email__iexact=email)
