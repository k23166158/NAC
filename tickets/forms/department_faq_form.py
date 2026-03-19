from django import forms

from ..models import DepartmentFAQ


class DepartmentFAQForm(forms.ModelForm):
    """Form for creating a department FAQ entry."""

    class Meta:
        """Meta configuration for DepartmentFAQForm."""

        model = DepartmentFAQ
        fields = ['question', 'answer']
        widgets = {
            'question': forms.TextInput(attrs={
                'class': 'department-form-input',
                'placeholder': 'Enter your question',
                'required': True,
            }),
            'answer': forms.Textarea(attrs={
                'class': 'department-form-textarea',
                'placeholder': 'Enter the answer',
                'rows': 4,
            }),
        }
        labels = {
            'question': 'Question',
            'answer': 'Answer',
        }
