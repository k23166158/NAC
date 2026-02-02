from django import forms
from tickets.models import Department


class CreateTicketForm(forms.Form):
    """Form used to create a ticket and its initial message."""
    title = forms.CharField(
        max_length=200,
        widget=forms.TextInput(attrs={
            "placeholder": "Short summary of your issue",
            "autocomplete": "off",
        }),
    )

    department = forms.ModelChoiceField(
        queryset=Department.objects.all(),
        empty_label="Select a department",
    )

    body = forms.CharField(
        label="Message",
        widget=forms.Textarea(attrs={
            "placeholder": "Describe your query in detail...",
            "rows": 6,
        }),
    )

    def clean_title(self):
        """Normalise and validate ticket title."""
        title = self.cleaned_data["title"].strip()
        if not title:
            raise forms.ValidationError("Title cannot be empty.")
        return title

    def clean_body(self):
        """Normalise and validate initial message body."""
        body = self.cleaned_data["body"].strip()
        if not body:
            raise forms.ValidationError("Message cannot be empty.")
        return body