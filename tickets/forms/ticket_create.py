from django import forms
from django.forms import ClearableFileInput
from tickets.models import Department


class MultipleFileInput(ClearableFileInput):
    """Custom widget that allows multiple file uploads."""
    allow_multiple_selected = True


class CreateTicketForm(forms.Form):
    """Form used to create a ticket and its initial message."""
    title = forms.CharField(
        max_length=200,
        required=False,
        widget=forms.TextInput(attrs={
            "class": "input",
            "placeholder": "Short summary of your issue",
            "autocomplete": "off",
        }),
    )

    departments = forms.ModelMultipleChoiceField(
        queryset=Department.objects.all(),
        required=True,
    )

    body = forms.CharField(
        label="Message",
        required=False,
        widget=forms.Textarea(attrs={
            "class": "textarea",
            "placeholder": "Describe your query in detail...",
            "rows": 10,
        }),
    )

    attachments = forms.FileField(
        label="Attachments",
        required=False,
        widget=MultipleFileInput(attrs={
            "class": "file-input",
            "accept": ".pdf,.doc,.docx,.xls,.xlsx,.ppt,.pptx,.zip,.jpg,.jpeg,.png,.gif,.txt",
        }),
    )

    def __init__(self, *args, **kwargs):
        """Initialize form to handle multiple file input."""
        super().__init__(*args, **kwargs)

    def clean_title(self):
        """Normalise and validate ticket title."""
        title = self.cleaned_data.get("title", "").strip()
        if not title:
            raise forms.ValidationError("Title cannot be empty.")
        return title

    def clean_body(self):
        """Normalise and validate initial message body."""
        body = self.cleaned_data.get("body", "").strip()
        if not body:
            raise forms.ValidationError("Message cannot be empty.")
        return body