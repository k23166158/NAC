import uuid
from datetime import datetime, timedelta

from django.db import transaction
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
    resolution_summary = models.TextField(blank=True, default="")
    closed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tickets_closed",
    )
    closed_at = models.DateTimeField(null=True, blank=True)
    reopened_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tickets_reopened",
    )
    reopened_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @classmethod
    def create_with_initial_message(cls, *, creator, cleaned_data, files=None):
        """Create a ticket with initial message, department assignments, and attachments."""
        from .ticket_message_attachments import TicketMessageAttachment

        with transaction.atomic():
            ticket = cls.objects.create(title=cleaned_data["title"], created_by=creator)
            message = cls._create_initial_message(ticket, creator, cleaned_data["body"])
            cls._create_ticket_assignments(ticket, cleaned_data["departments"])
            TicketMessageAttachment.create_for_message(ticket, message, files, creator)
        return ticket

    @staticmethod
    def _create_initial_message(ticket, creator, body):
        """Create the first user message for a ticket."""
        from .ticket_message import TicketMessage

        return TicketMessage.objects.create(ticket=ticket, body=body, sender=creator)

    @staticmethod
    def _create_ticket_assignments(ticket, departments):
        """Persist department assignments for a ticket."""
        from .ticket_assigned import TicketAssigned

        assignments = TicketAssigned.build_for_departments(ticket, departments)
        TicketAssigned.objects.bulk_create(assignments)

    @classmethod
    def status_counts(cls):
        """Return ticket counts grouped by status keys used by dashboard."""
        return {
            "open": cls.objects.filter(status=cls.Status.OPEN).count(),
            "pending": cls.objects.filter(status=cls.Status.PENDING).count(),
            "closed": cls.objects.filter(status=cls.Status.CLOSED).count(),
        }

    @classmethod
    def admin_ticket_stats(cls):
        """Return admin ticket statistics payload."""
        return {"total": cls.objects.count(), **cls.status_counts()}

    @classmethod
    def allowed_scopes_for(cls, user):
        """Return visible ticket scopes for a user."""
        if not user.is_staff:
            return ["personal"]
        return ["personal", "department", "assigned"]

    @classmethod
    def normalize_scope_for(cls, user, scope):
        """Return a valid ticket scope for the given user."""
        return scope if scope in cls.allowed_scopes_for(user) else "personal"

    @classmethod
    def search_filters_from(cls, data):
        """Build normalized search filters from request query params."""
        return {
            "scope": data.get("scope", "personal"),
            "q": (data.get("q") or "").strip(),
            "status": data.get("status", ""),
            "department": data.get("department", ""),
            "assigned_staff": data.get("assigned_staff", ""),
            "created_from": data.get("created_from", ""),
            "created_to": data.get("created_to", ""),
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
    def search_page_queryset(cls, user, filters):
        """Return filtered ticket queryset for the ticket search page."""
        scope = cls.normalize_scope_for(user, filters.get("scope"))
        queryset = cls.base_for_scope(user, scope=scope)
        if queryset is None:
            return cls.objects.none()
        queryset = queryset.select_related("created_by")
        queryset = cls._annotate_last_message_for_user(queryset, user)
        queryset = cls._annotate_unread_count_for_user(queryset, user)
        queryset = cls._apply_search_filters(queryset, filters)
        return queryset.order_by("-updated_at").distinct()

    @classmethod
    def _apply_search_filters(cls, queryset, filters):
        """Apply all ticket search filters to a queryset."""
        queryset = cls._filter_search_text(queryset, filters.get("q"))
        queryset = cls._filter_status(queryset, filters.get("status"))
        queryset = cls._filter_department(queryset, filters.get("department"))
        queryset = cls._filter_assigned_staff(queryset, filters.get("assigned_staff"))
        queryset = cls._filter_created_from(queryset, filters.get("created_from"))
        return cls._filter_created_to(queryset, filters.get("created_to"))

    @staticmethod
    def _filter_search_text(queryset, search_text):
        """Filter tickets by title, body, or creator fields."""
        if not search_text:
            return queryset
        return queryset.filter(
            Q(title__icontains=search_text)
            | Q(messages__body__icontains=search_text)
            | Q(created_by__username__icontains=search_text)
            | Q(created_by__first_name__icontains=search_text)
            | Q(created_by__last_name__icontains=search_text)
            | Q(created_by__email__icontains=search_text)
        )

    @classmethod
    def _filter_status(cls, queryset, status):
        """Filter tickets by valid status."""
        if status not in {cls.Status.OPEN, cls.Status.PENDING, cls.Status.CLOSED}:
            return queryset
        return queryset.filter(status=status)

    @staticmethod
    def _filter_department(queryset, department_id):
        """Filter tickets by department assignment."""
        if not department_id:
            return queryset
        return queryset.filter(
            Q(assignments__department_id=department_id)
            | Q(ticket_departments__department_id=department_id)
        )

    @staticmethod
    def _filter_assigned_staff(queryset, staff_id):
        """Filter tickets by explicitly assigned staff participant."""
        if not staff_id:
            return queryset
        return queryset.filter(participants__user_id=staff_id, participants__removed_self=False)

    @staticmethod
    def _filter_created_from(queryset, created_from):
        """Filter tickets created on or after the provided date."""
        if not created_from:
            return queryset
        return queryset.filter(created_at__date__gte=created_from)

    @staticmethod
    def _filter_created_to(queryset, created_to):
        """Filter tickets created on or before the provided date."""
        if not created_to:
            return queryset
        return queryset.filter(created_at__date__lte=created_to)

    @classmethod
    def search_filter_options(cls, user, scope, department_id="", staff_id=""):
        """Return department and staff filter options visible in a scope."""
        queryset = cls.base_for_scope(user, scope=scope)
        if queryset is None:
            return {"departments": [], "staff_users": []}
        return {
            "departments": cls._department_filter_options(queryset, staff_id),
            "staff_users": cls._staff_filter_options(queryset, department_id),
        }

    @staticmethod
    def _department_filter_options(queryset, staff_id=""):
        """Return department options for tickets in queryset."""
        from .department import Department

        options = Department.objects.filter(
            Q(assigned_tickets__ticket__in=queryset)
            | Q(ticket_departments__ticket__in=queryset)
        )
        if staff_id:
            options = options.filter(assigned_users__user_id=staff_id)
        return options.distinct().order_by("name")

    @staticmethod
    def _staff_filter_options(queryset, department_id=""):
        """Return assigned staff options for tickets in queryset."""
        user_model = get_user_model()
        options = user_model.objects.filter(
            ticket_participations__ticket__in=queryset,
            ticket_participations__removed_self=False,
        )
        if department_id:
            options = options.filter(user__department_id=department_id)
        return options.distinct().order_by("last_name", "first_name", "username")

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
        return self.close_with_resolution()

    @staticmethod
    def _performed_by_name(performed_by):
        """Return a display name for a lifecycle user."""
        if performed_by is None:
            return "System"
        return performed_by.get_full_name() or performed_by.username

    @staticmethod
    def _clean_resolution_summary(resolution_summary):
        """Return a normalized resolution summary string."""
        return (resolution_summary or "").strip()

    def _close_update_fields(self):
        """Return fields persisted for a close action."""
        return ["status", "resolution_summary", "closed_by", "closed_at", "reopened_by", "reopened_at", "updated_at"]

    def _reopen_update_fields(self):
        """Return fields persisted for a reopen action."""
        return ["status", "reopened_by", "reopened_at", "updated_at"]

    def _set_closed_state(self, performed_by, resolution_summary):
        """Apply in-memory close state."""
        self.status = self.Status.CLOSED
        self.resolution_summary = resolution_summary
        self.closed_by = performed_by
        self.closed_at = timezone.now()
        self.reopened_by = None
        self.reopened_at = None

    def _set_reopened_state(self, performed_by):
        """Apply in-memory reopen state."""
        self.status = self.Status.OPEN
        self.reopened_by = performed_by
        self.reopened_at = timezone.now()

    def _close_system_messages(self, resolution_summary, performed_by):
        """Create thread history entries for closing a ticket."""
        from .ticket_message import TicketMessage

        TicketMessage.create_system_message(self, f"Ticket closed by {self._performed_by_name(performed_by)}.")
        if resolution_summary:
            TicketMessage.create_system_message(self, f"Resolution summary: {resolution_summary}")

    def _reopen_system_message(self, performed_by):
        """Create a thread history entry for reopening a ticket."""
        from .ticket_message import TicketMessage

        TicketMessage.create_system_message(self, f"Ticket reopened by {self._performed_by_name(performed_by)}.")

    def close_with_resolution(self, performed_by=None, resolution_summary=""):
        """Close ticket and persist lifecycle metadata."""
        resolution_summary = self._clean_resolution_summary(resolution_summary)
        if self.status == self.Status.CLOSED:
            return False
        self._set_closed_state(performed_by, resolution_summary)
        self.save(update_fields=self._close_update_fields())
        self._close_system_messages(resolution_summary, performed_by)
        return True

    def reopen(self, performed_by=None):
        """Reopen a closed ticket and persist lifecycle metadata."""
        if self.status != self.Status.CLOSED:
            return False
        self._set_reopened_state(performed_by)
        self.save(update_fields=self._reopen_update_fields())
        self._reopen_system_message(performed_by)
        return True

    def __str__(self):
        """Returns a string representation of the ticket."""
        return f"#{self.id} - {self.title}"
    
