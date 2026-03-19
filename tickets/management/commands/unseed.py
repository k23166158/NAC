from django.core.management.base import BaseCommand
from tickets.models import SeededObject

class Command(BaseCommand):
    """Build automation command to unseed the database."""

    def handle(self, *args, **options):
        """
        Django entrypoint for the command.
        
        Deletes all data created by the seed command to allow for a fresh start.
        """
        print("Unseeding data...")
        seeded_objects = list(
            SeededObject.objects.select_related("content_type").order_by("-id")
        )

        removed = 0
        for seeded in seeded_objects:
            model = seeded.content_type.model_class()
            if model is None:
                continue
            deleted, _ = model.objects.filter(pk=seeded.object_id).delete()
            if deleted:
                removed += 1

        SeededObject.objects.all().delete()
        print(f"Unseeding complete. Removed {removed} tracked objects.")
