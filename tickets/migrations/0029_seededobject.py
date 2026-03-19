from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("contenttypes", "0002_remove_content_type_name"),
        ("tickets", "0028_ticket_resolution_workflow"),
    ]

    operations = [
        migrations.CreateModel(
            name="SeededObject",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("object_id", models.PositiveIntegerField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("content_type", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="contenttypes.contenttype")),
            ],
        ),
        migrations.AddConstraint(
            model_name="seededobject",
            constraint=models.UniqueConstraint(
                fields=("content_type", "object_id"),
                name="unique_seeded_object_reference",
            ),
        ),
    ]

