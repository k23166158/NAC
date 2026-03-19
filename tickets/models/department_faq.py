from django.conf import settings
from django.db import models


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

    def __str__(self):
        return f"{self.department.name}: {self.question[:60]}"

    class Meta:
        ordering = ["order", "created_on"]
