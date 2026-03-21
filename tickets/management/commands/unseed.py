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
        summary = self._unseed_summary()
        self.stdout.write(self._summary_message(summary))

    def _unseed_summary(self):
        """Run all unseed steps and return a summary dictionary."""
        attachment_count = self._delete_attachment_files()
        profile_picture_count = self._delete_profile_pictures()
        deleted_counts = self._delete_seeded_records()
        self._cleanup_empty_media_directories()
        return {
            "attachment_count": attachment_count,
            "profile_picture_count": profile_picture_count,
            "deleted_counts": deleted_counts,
        }

    def _summary_message(self, summary):
        """Return the completion message for the unseed command."""
        deleted_counts = summary["deleted_counts"]
        return (
            "Unseeding complete. "
            f"Deleted {deleted_counts['users']} users, "
            f"{deleted_counts['departments']} departments, "
            f"{deleted_counts['tickets']} tickets, "
            f"{deleted_counts['notifications']} notifications, "
            f"{deleted_counts['faqs']} FAQs, "
            f"{summary['attachment_count']} attachment files, and "
            f"{summary['profile_picture_count']} profile pictures."
        )

    def _delete_attachment_files(self):
        """Delete uploaded ticket attachment files from storage."""
        attachments = [a for a in TicketMessageAttachment.objects.exclude(file="") if a.file]
        for attachment in attachments:
            attachment.file.delete(save=False)
        return len(attachments)

    def _delete_profile_pictures(self):
        """Delete uploaded profile picture files from storage."""
        users = [user for user in User.objects.exclude(profile_picture="") if user.profile_picture]
        for user in users:
            user.profile_picture.delete(save=False)
        return len(users)

    @transaction.atomic
    def _delete_seeded_records(self):
        """Delete seeded rows from all application tables."""
        counts = self._record_counts()
        self._delete_all_seeded_querysets()
        return counts

    def _record_counts(self):
        """Return counts for models cleared by unseed."""
        model_counts = [
            ("notifications", Notification),
            ("ticket_departments", TicketDepartment),
            ("ticket_assignments", TicketAssigned),
            ("participants", TicketParticipant),
            ("attachments", TicketMessageAttachment),
            ("messages", TicketMessage),
            ("invitations", DepartmentInvitation),
            ("user_departments", UserDepartments),
            ("faqs", DepartmentFAQ),
            ("tickets", Ticket),
            ("departments", Department),
            ("users", User),
        ]
        return {name: model.objects.count() for name, model in model_counts}

    def _delete_all_seeded_querysets(self):
        """Delete all seeded rows in dependency-safe order."""
        querysets = [
            Notification.objects.all(),
            TicketDepartment.objects.all(),
            TicketAssigned.objects.all(),
            TicketParticipant.objects.all(),
            TicketMessageAttachment.objects.all(),
            TicketMessage.objects.all(),
            DepartmentInvitation.objects.all(),
            UserDepartments.objects.all(),
            DepartmentFAQ.objects.all(),
            Ticket.objects.all(),
            Department.objects.all(),
            User.objects.all(),
        ]
        for queryset in querysets:
            queryset.delete()

    def _cleanup_empty_media_directories(self):
        """Remove empty media subdirectories left behind after file deletion."""
        media_root = Path("media")
        if not media_root.exists():
            return
        for directory in self._empty_media_directories(media_root):
            directory.rmdir()

    def _empty_media_directories(self, media_root):
        """Return empty media directories in deepest-first order."""
        directories = [path for path in media_root.rglob("*") if path.is_dir()]
        ordered_directories = sorted(
            directories,
            key=lambda path: len(path.parts),
            reverse=True,
        )
        return [directory for directory in ordered_directories if not any(directory.iterdir())]
