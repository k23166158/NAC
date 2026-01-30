import uuid

from django.db import migrations, models


def set_ticket_uuids(apps, schema_editor):
    Ticket = apps.get_model("tickets", "Ticket")
    for ticket in Ticket.objects.all():
        ticket.uuid = uuid.uuid4()
        ticket.save(update_fields=["uuid"])


class Migration(migrations.Migration):

    dependencies = [
        ("tickets", "0009_merge_20260130_2056"),
    ]

    operations = [
        migrations.AddField(
            model_name="ticket",
            name="uuid",
            field=models.UUIDField(db_index=True, editable=False, null=True, unique=True),
        ),
        migrations.RunPython(set_ticket_uuids, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="ticket",
            name="uuid",
            field=models.UUIDField(db_index=True, default=uuid.uuid4, editable=False, unique=True),
        ),
    ]
