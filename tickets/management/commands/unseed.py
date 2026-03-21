from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction

from tickets.models import (
    Department,
    DepartmentFAQ,
    DepartmentInvitation,
    Notification,
    Ticket,
    TicketAssigned,
    TicketDepartment,
    TicketMessage,
    TicketMessageAttachment,
    TicketParticipant,
    UserDepartments,
)

User = get_user_model()


class Command(BaseCommand):
    """Build automation command to unseed the database."""

    def handle(self, *args, **options):
        """
        Delete all seeded application data and cleanup uploaded media files.
        """
        self.stdout.write("Unseeding data...")

        attachment_count = self._delete_attachment_files()
        profile_picture_count = self._delete_profile_pictures()
        deleted_counts = self._delete_seeded_records()
        self._cleanup_empty_media_directories()

        self.stdout.write(
            "Unseeding complete. "
            f"Deleted {deleted_counts['users']} users, "
            f"{deleted_counts['departments']} departments, "
            f"{deleted_counts['tickets']} tickets, "
            f"{deleted_counts['notifications']} notifications, "
            f"{deleted_counts['faqs']} FAQs, "
            f"{attachment_count} attachment files, and "
            f"{profile_picture_count} profile pictures."
        )

    def _delete_attachment_files(self):
        """Delete uploaded ticket attachment files from storage."""
        deleted = 0
        for attachment in TicketMessageAttachment.objects.exclude(file=""):
            if attachment.file:
                attachment.file.delete(save=False)
                deleted += 1
        return deleted

    def _delete_profile_pictures(self):
        """Delete uploaded profile picture files from storage."""
        deleted = 0
        for user in User.objects.exclude(profile_picture=""):
            if user.profile_picture:
                user.profile_picture.delete(save=False)
                deleted += 1
        return deleted

    @transaction.atomic
    def _delete_seeded_records(self):
        """Delete seeded rows from all application tables."""
        counts = {
            "notifications": Notification.objects.count(),
            "ticket_departments": TicketDepartment.objects.count(),
            "ticket_assignments": TicketAssigned.objects.count(),
            "participants": TicketParticipant.objects.count(),
            "attachments": TicketMessageAttachment.objects.count(),
            "messages": TicketMessage.objects.count(),
            "invitations": DepartmentInvitation.objects.count(),
            "user_departments": UserDepartments.objects.count(),
            "faqs": DepartmentFAQ.objects.count(),
            "tickets": Ticket.objects.count(),
            "departments": Department.objects.count(),
            "users": User.objects.count(),
        }

        Notification.objects.all().delete()
        TicketDepartment.objects.all().delete()
        TicketAssigned.objects.all().delete()
        TicketParticipant.objects.all().delete()
        TicketMessageAttachment.objects.all().delete()
        TicketMessage.objects.all().delete()
        DepartmentInvitation.objects.all().delete()
        UserDepartments.objects.all().delete()
        DepartmentFAQ.objects.all().delete()
        Ticket.objects.all().delete()
        Department.objects.all().delete()
        User.objects.all().delete()

        return counts

    def _cleanup_empty_media_directories(self):
        """Remove empty media subdirectories left behind after file deletion."""
        media_root = Path("media")
        if not media_root.exists():
            return

        for directory in sorted(
            (path for path in media_root.rglob("*") if path.is_dir()),
            key=lambda path: len(path.parts),
            reverse=True,
        ):
            if not any(directory.iterdir()):
                directory.rmdir()
