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

    def _check_reserved_slug(self, slug, name):
        """Check if slug is a reserved word."""
        reserved_slugs = ['create', 'edit', 'delete', 'manage']
        if slug in reserved_slugs:
            raise ValidationError(
                f'"{name}" is a reserved name and cannot be used for a department. Please choose a different name.'
            )

    def clean_name(self):
        """Validate that the department name is unique and not a reserved word."""
        name = self.cleaned_data.get('name')
        if not name:
            return name
        slug = slugify(name)
        self._check_reserved_slug(slug, name)
        existing = Department.objects.filter(slug=slug).first()
        if existing and existing != self.instance:
            raise ValidationError(
                'A department with this name already exists. Please choose a different name.'
            )
        return name

