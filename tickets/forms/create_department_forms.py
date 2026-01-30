from django import forms
from django.core.exceptions import ValidationError
from django.utils.text import slugify

from ..models import Department


class CreateDepartmentForm(forms.ModelForm):
    """Form for creating a new department."""
    
    class Meta:
        """Meta configuration for CreateDepartmentForm."""
        model = Department
        fields = ['name', 'description']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'department-form-input',
                'placeholder': 'Enter department name',
                'required': True,
            }),
            'description': forms.Textarea(attrs={
                'class': 'department-form-textarea',
                'placeholder': 'Enter department description (optional)',
                'rows': 4,
            }),
        }
        labels = {
            'name': 'Department Name',
            'description': 'Description',
        }
        help_texts = {
            'name': 'A unique name for the department',
            'description': 'Optional description of the department',
        }

    def clean_name(self):
        """Validate that the department name is unique."""
        name = self.cleaned_data.get('name')
        if not name:
            return name
        slug = slugify(name)
        existing = Department.objects.filter(slug=slug).first()
        if existing and existing != self.instance:
            raise ValidationError(
                'A department with this name already exists. Please choose a different name.'
            )
        return name

