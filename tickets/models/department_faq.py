from django.conf import settings
from django.db import models
from django.shortcuts import get_object_or_404


class DepartmentFAQ(models.Model):
    """Model representing a FAQ entry for a department."""

    department = models.ForeignKey(
        "tickets.Department",
        on_delete=models.CASCADE,
        related_name="faqs",
    )
    question = models.CharField(max_length=500)
    answer = models.TextField()
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="faqs_created",
    )
    created_on = models.DateTimeField(auto_now_add=True)
    order = models.PositiveIntegerField(default=0)

    @classmethod
    def create_from_form(cls, form, *, department, actor):
        """Create a department FAQ from a valid form."""
        faq = form.save(commit=False)
        faq.department = department
        faq.created_by = actor
        faq.save()
        return faq

    @classmethod
    def update_from_form(cls, form):
        """Update an existing department FAQ from a valid form."""
        return form.save()

    @classmethod
    def get_for_department_or_404(cls, *, faq_id, department):
        """Return a department FAQ scoped to the given department."""
        return get_object_or_404(cls, id=faq_id, department=department)

    def delete_for_department(self, department):
        """Delete the FAQ when it belongs to the expected department."""
        if self.department_id != department.id:
            return False
        self.delete()
        return True

    def __str__(self):
        """Return string representation of the FAQ."""
        return f"{self.department.name}: {self.question[:60]}"

    class Meta:
        """Meta options for the DepartmentFAQ model."""

        ordering = ["order", "created_on"]
