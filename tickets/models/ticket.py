import uuid
from datetime import datetime, timedelta

from django.db import models
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db.models import Count, DateTimeField, F, OuterRef, Q, Subquery
from django.db.models.functions import Coalesce
from django.utils import timezone


class Ticket(models.Model):
    """Represents a support ticket in the system."""

    class Status(models.TextChoices):
        """Represents the status of a support ticket."""
        OPEN = 'open', 'Open'
        PENDING = 'pending', 'Pending'
        CLOSED = 'closed', 'Closed'

    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, db_index=True)
    title = models.CharField(max_length=200)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.OPEN
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='tickets_created'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @classmethod
    def status_counts(cls):
        """Return ticket counts grouped by status keys used by dashboard."""
        return {
            "open": cls.objects.filter(status=cls.Status.OPEN).count(),
            "pending": cls.objects.filter(status=cls.Status.PENDING).count(),
            "closed": cls.objects.filter(status=cls.Status.CLOSED).count(),
        }

    @classmethod
    def base_for_scope(cls, user, scope="personal"):
        """Return tickets visible to a user for a dashboard scope."""
        if scope == "personal":
            return (
                cls.objects.filter(created_by=user).exclude(participants__user=user,participants__removed_self=True,).distinct()
            )
        if scope == "department":
            return (
                cls.objects.filter(assignments__department__assigned_users__user=user).exclude(participants__user=user,participants__removed_self=True,).distinct()
            )
        if scope == "assigned":
            return cls.objects.filter(participants__user=user,participants__removed_self=False,).distinct()
        return None

    @classmethod
    def _annotate_last_message_for_user(cls, qs, user):
        """Annotate dashboard fields derived from the latest message."""
        from .ticket_message import TicketMessage
        from .ticket_participant import TicketParticipant

        last_msg = TicketMessage.objects.filter(ticket_id=OuterRef("pk")).order_by("-edited_at")
        last_read = TicketParticipant.objects.filter(
            ticket=OuterRef("pk"), user=user
        ).values("last_read_at")[:1]
        annotations = cls._last_message_annotations(last_msg, last_read)
        return qs.annotate(**annotations)

    @classmethod
    def _last_message_annotations(cls, last_msg, last_read):
        """Return dashboard annotations derived from the latest message subqueries."""
        return {
            "last_message_at": Subquery(last_msg.values("edited_at")[:1]),
            "last_message_body": Subquery(last_msg.values("body")[:1]),
            "last_message_sender_id": Subquery(last_msg.values("sender_id")[:1]),
            "last_sender_is_staff": Subquery(last_msg.values("sender__is_staff")[:1]),
            "last_sender_first": Subquery(last_msg.values("sender__first_name")[:1]),
            "last_sender_last": Subquery(last_msg.values("sender__last_name")[:1]),
            "user_last_read_at": Subquery(last_read, output_field=DateTimeField()),
        }

    @classmethod
    def _annotate_unread_count_for_user(cls, qs, user):
        """Annotate unread message counts for the given user."""
        return qs.annotate(
            unread_count=Count(
                "messages",
                filter=Q(messages__edited_at__gt=Coalesce(
                    F("user_last_read_at"),
                    timezone.make_aware(datetime.min),
                )) & ~Q(messages__sender=user),
            )
        )

    @classmethod
    def annotated_for_home(cls, user, scope="personal"):
        """Return tickets for the scope with dashboard annotations."""
        qs = cls.base_for_scope(user, scope=scope)
        if qs is None:
            return None
        qs = cls._annotate_last_message_for_user(qs, user)
        return cls._annotate_unread_count_for_user(qs, user)

    @classmethod
    def completed_from(cls, qs):
        """Return completed tickets from an annotated queryset."""
        return qs.filter(status=cls.Status.CLOSED).order_by("-updated_at")

    @classmethod
    def overdue_from(cls, qs, *, days=7):
        """Return overdue open/pending tickets based on latest non-staff message age."""
        cutoff = timezone.now() - timedelta(days=days)
        return qs.filter(
            status__in=[cls.Status.OPEN, cls.Status.PENDING],
            last_message_at__isnull=False,
            last_message_at__lt=cutoff,
            last_sender_is_staff=False,
        ).order_by("-last_message_at")

    @classmethod
    def active_from(cls, qs, overdue):
        """Return active (non-overdue) open/pending tickets."""
        return qs.filter(
            status__in=[cls.Status.OPEN, cls.Status.PENDING],
        ).exclude(
            id__in=overdue.values_list("id", flat=True)
        ).order_by("-updated_at")

    def mark_read_for(self, user):
        """Create/update participant read marker for this user."""
        from .ticket_participant import TicketParticipant

        return TicketParticipant.objects.update_or_create(
            ticket=self,
            user=user,
            defaults={"last_read_at": timezone.now()},
        )

    def touch(self):
        """Bump updated_at to now."""
        type(self).objects.filter(id=self.id).update(updated_at=timezone.now())

    def get_ticket_staff(self):
        """Return users explicitly assigned as participants on this ticket."""
        return [p.user for p in self.participants.select_related("user") if not p.removed_self]

    def get_department_staff(self):
        """Return users from departments assigned to this ticket."""
        User = get_user_model()
        return User.objects.filter(
            user__department__assigned_tickets__ticket=self
        ).distinct()

    def can_edit(self, user):
        """Return whether user can edit this ticket thread."""
        return (
            user.is_superuser
            or self.created_by == user
            or user in self.get_ticket_staff()
            or user in self.get_department_staff()
        )

    def close(self):
        """Close ticket if not already closed."""
        if self.status == self.Status.CLOSED:
            return False
        self.status = self.Status.CLOSED
        self.save(update_fields=["status", "updated_at"])
        self.touch()
        return True

    def __str__(self):
        """Returns a string representation of the ticket."""
        return f"#{self.id} - {self.title}"
    
