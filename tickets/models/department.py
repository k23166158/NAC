from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.paginator import Paginator
from django.db.models import OuterRef, Prefetch, Subquery
from django.db import models
from django.shortcuts import get_object_or_404
from django.utils.text import slugify
from .notification import Notification
from tickets.helpers.notifications import create_notification
from datetime import timedelta
from django.utils import timezone
from django.db.models.functions import Coalesce

from .ticket import Ticket
from .ticket_message import TicketMessage

User = get_user_model()


class Department(models.Model):
    """Model representing a department within the ticketing system."""
    name = models.CharField(max_length=255)
    description = models.TextField(max_length=1023, blank=True)
    slug = models.SlugField(max_length=255, unique=True, blank=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="departments_created",
    )

    members = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name="departments",
        limit_choices_to={"is_staff": True},
        blank=True,
    )

    created_on = models.DateTimeField(auto_now_add=True)

    @classmethod
    def get_by_slug_or_404(cls, slug):
        """Return a department by slug or raise 404."""
        return get_object_or_404(cls, slug=slug)

    @classmethod
    def assigned_to_user_with_ticket_counts(cls, user, search_query=""):
        """Return departments assigned to user with ticket count annotations."""
        queryset = cls._assigned_to_user_queryset(user)
        queryset = cls._filter_manage_search(queryset, search_query)
        queryset = queryset.annotate(**cls._ticket_count_annotations())
        return queryset.prefetch_related("assigned_users__user").order_by("name")

    @classmethod
    def browsable_with_active_member_counts(cls, search_query=""):
        """Return all departments for non-staff browsing."""
        queryset = cls.objects.select_related("created_by")
        queryset = cls._filter_manage_search(queryset, search_query)
        queryset = queryset.annotate(active_member_count=cls._active_member_count())
        return queryset.prefetch_related(cls._active_member_prefetch()).order_by("name")

    @classmethod
    def _assigned_to_user_queryset(cls, user):
        """Return base queryset for departments assigned to user."""
        return cls.objects.filter(assigned_users__user=user).select_related("created_by").distinct()

    @staticmethod
    def _ticket_count_annotations():
        """Return annotations for active and completed ticket counts."""
        return {
            "active_ticket_count": models.Count(
                "assigned_tickets",
                filter=models.Q(assigned_tickets__ticket__status__in=["open", "pending"]),
                distinct=True,
            ),
            "completed_ticket_count": models.Count(
                "assigned_tickets",
                filter=models.Q(assigned_tickets__ticket__status="closed"),
                distinct=True,
            ),
        }

    @staticmethod
    def _active_member_count():
        """Return an annotation counting active department members."""
        return models.Count(
            "assigned_users",
            filter=models.Q(assigned_users__user__is_active=True),
            distinct=True,
        )

    @staticmethod
    def _active_member_prefetch():
        """Prefetch active membership rows and attached users."""
        from .user_departments import UserDepartments

        return Prefetch(
            "assigned_users",
            queryset=UserDepartments.objects.select_related("user").filter(user__is_active=True),
            to_attr="active_assignments",
        )

    @staticmethod
    def _filter_manage_search(queryset, search_query):
        """Filter manage departments queryset by name/description."""
        if not search_query:
            return queryset
        return queryset.filter(
            models.Q(name__icontains=search_query)
            | models.Q(description__icontains=search_query)
        )

    def can_view(self, user):
        """Check if user may view this department."""
        from .user_departments import UserDepartments

        return user.is_superuser or UserDepartments.objects.filter(
            user=user,
            department=self,
        ).exists()

    def can_manage_staff(self, user):
        """Check if user may manage staff for this department."""
        return user.is_superuser or (user.is_staff and self.created_by == user)

    def can_manage_faqs(self, user):
        """Check if user may add or delete FAQs for this department."""
        from .user_departments import UserDepartments

        return user.is_superuser or UserDepartments.objects.filter(
            user=user,
            department=self,
        ).exists()

    def get_current_staff(self):
        """Return users currently assigned to this department."""
        return [assignment.user for assignment in self.assigned_users.select_related("user").all()]

    def get_active_staff(self):
        """Return active users currently assigned to this department."""
        return [assignment.user for assignment in self._active_assignments()]

    def _active_assignments(self):
        """Return active user-department assignments."""
        cached = getattr(self, "active_assignments", None)
        if cached is not None:
            return cached
        return list(self.assigned_users.select_related("user").filter(user__is_active=True))

    def get_pending_invitations(self):
        """Return pending invitations for this department."""
        from .department_invitation import DepartmentInvitation

        return DepartmentInvitation.objects.filter(
            department=self,
            status="pending",
        ).select_related("recipient")

    def get_available_staff(self, current_staff, invited_users):
        """Return staff users who are not assigned and not already invited."""
        current_ids = [u.id for u in current_staff] + [u.id for u in invited_users]
        return User.objects.filter(is_staff=True).exclude(id__in=current_ids)

    @staticmethod
    def annotate_tickets(queryset):
        """Annotate tickets with latest message metadata."""
        last_msg = TicketMessage.objects.filter(ticket_id=OuterRef("pk")).order_by("-edited_at")
        return queryset.annotate(
            last_message_at=Subquery(last_msg.values("edited_at")[:1]),
            last_message_body=Subquery(last_msg.values("body")[:1]),
            last_message_sender_id=Subquery(last_msg.values("sender_id")[:1]),
            last_sender_slug=Subquery(last_msg.values("sender__profile_slug")[:1]),
            last_sender_is_staff=Subquery(last_msg.values("sender__is_staff")[:1]),
            last_sender_first=Subquery(last_msg.values("sender__first_name")[:1]),
            last_sender_last=Subquery(last_msg.values("sender__last_name")[:1]),
        )

    def get_tickets(self, status_list):
        """Return department tickets for the provided status list, sorting overdue tickets to the top."""
        qs = Ticket.objects.filter(assignments__department=self, status__in=status_list)
        qs = Department.annotate_tickets(qs)
        cutoff = timezone.now() - timedelta(days=7)
        return qs.annotate(
            effective_date=Coalesce("updated_at", "created_at")
        ).annotate(
            overdue_sort=models.Case(
                models.When(models.Q(status="open") & models.Q(effective_date__lt=cutoff), then=models.Value(0)),
                default=models.Value(1),
                output_field=models.IntegerField()
            )
        ).order_by("overdue_sort", "-updated_at")

    def build_view_context(self, request):
        """Build the context payload for the department details page."""
        from tickets.forms import DepartmentFAQForm

        current_staff = self.get_current_staff()
        invited_users = self._get_invited_users()
        context = {"department": self, "staff": current_staff}
        context.update(self._staff_context(request, current_staff, invited_users))
        context.update(self._ticket_context(request))
        context["faqs"] = self.faqs.select_related("created_by").all()
        context["faq_form"] = DepartmentFAQForm()
        context["user_can_manage_faqs"] = self.can_manage_faqs(request.user)
        return context

    def build_public_view_context(self, request):
        """Build the read-only department context for non-staff users."""
        active_staff = self.get_active_staff()
        return {
            "department": self,
            "staff_page": self._paginate_queryset(request, active_staff, "staff_page", per_page=10),
            "staff_total": len(active_staff),
            "faqs": self.faqs.select_related("created_by").all(),
            "is_public_department_view": True,
        }

    def _get_invited_users(self):
        """Return users with pending invitations for this department."""
        return [invite.recipient for invite in self.get_pending_invitations()]

    def _staff_context(self, request, current_staff, invited_users):
        """Return staff-related context for the department page."""
        all_members = current_staff + invited_users
        staff_page = self._paginate_queryset(
            request, all_members, "staff_page", per_page=10
        )
        staff_total = len(all_members)
        return {
            "staff_page": staff_page,
            "staff_total": staff_total,
            "invited_users": invited_users,
            "available_staff": self.get_available_staff(current_staff, invited_users),
        }

    def _ticket_context(self, request):
        """Return ticket-related context for the department page."""
        active_tickets = self.get_tickets([Ticket.Status.OPEN])
        closed_tickets = self.get_tickets([Ticket.Status.CLOSED])
        return self._ticket_context_dict(request, active_tickets, closed_tickets)

    def _ticket_context_dict(self, request, active_tickets, closed_tickets):
        """Build and return the ticket context dictionary."""
        ctx = {}
        ctx.update(self._ticket_section_context(request, active_tickets, "active", ["staff_page", "closed_page"]))
        ctx.update(self._ticket_section_context(request, closed_tickets, "closed", ["staff_page", "active_page"]))
        ctx["active_tickets_preview"] = active_tickets
        ctx["closed_tickets_preview"] = closed_tickets
        return ctx

    def _ticket_section_context(self, request, tickets, prefix, exclude_params):
        """Build context entries for a single ticket status group."""
        page_param = f"{prefix}_page"
        preserve = self._build_preserve_params(request, exclude_params)
        return {
            f"{prefix}_tickets": tickets,
            f"{prefix}_tickets_page": self._paginate_queryset(request, tickets, page_param, per_page=10),
            f"{prefix}_tickets_count": tickets.count(),
            f"{prefix}_tickets_preserve_params": preserve,
        }

    @staticmethod
    def _build_preserve_params(request, param_names):
        """Build a query string for preserving specified parameters."""
        params = [
            f"&{name}={request.GET[name]}"
            for name in param_names
            if name in request.GET
        ]
        return "".join(params)

    @staticmethod
    def _paginate_queryset(request, queryset, page_param, *, per_page):
        """Return a page object for the given queryset/list."""
        paginator = Paginator(queryset, per_page)
        return paginator.get_page(request.GET.get(page_param))

    def process_staff_change(self, *, actor, user_id, action):
        """Apply add/remove/remove_invite staff action for this department."""
        if not user_id:
            return None

        user = get_object_or_404(User, id=user_id)
        handlers = self._staff_change_handlers(actor, user)
        handler = handlers.get(action)
        return handler() if handler else None

    def _staff_change_handlers(self, actor, user):
        """Return handlers for staff management actions."""
        return {
            "add": lambda: self.invite_staff(actor=actor, user=user),
            "remove": lambda: self._remove_staff(actor=actor, user=user),
            "remove_invite": lambda: self._remove_pending_invite(user),
        }

    def _remove_staff(self, actor, user):
        """Remove a user from this department."""
        from .user_departments import UserDepartments

        deleted_count, _ = UserDepartments.objects.filter(user=user, department=self).delete()
        if deleted_count > 0:
            create_notification(
                user=user,
                actor=actor,
                notification_type=Notification.NotificationType.DEPT_MEMBER_REMOVED,
                target_object=self,
            )
        return None

    def _remove_pending_invite(self, user):
        """Delete any pending invite for a user in this department."""
        from .department_invitation import DepartmentInvitation

        DepartmentInvitation.objects.filter(
            department=self,
            recipient=user,
            status="pending",
        ).delete()
        return None

    def invite_staff(self, *, actor, user):
        """Create a pending invite for a staff user if allowed."""
        validation = self._validate_invitable_staff(user)
        if validation:
            return validation
        return self._create_staff_invite(actor=actor, user=user)

    def _validate_invitable_staff(self, user):
        """Return validation error/warning tuple when user cannot be invited."""
        from .user_departments import UserDepartments

        if not user.is_staff:
            return ("error", "Only staff users can be invited to a department.")
        if UserDepartments.objects.filter(user=user, department=self).exists():
            name = user.get_full_name() or user.username
            return ("warning", f"{name} is already in this department.")
        return None

    def _create_staff_invite(self, *, actor, user):
        """Create or reuse a pending invite and return message tuple."""
        from .department_invitation import DepartmentInvitation

        _invite, created = DepartmentInvitation.objects.get_or_create(
            department=self, recipient=user,
            status="pending", defaults={"sender": actor},
        )
        name = user.get_full_name() or user.username
        if created:
            create_notification(
                user=user, actor=actor,
                notification_type=Notification.NotificationType.DEPT_INVITED, target_object=self,
            )
            return ("success", f"Invitation sent to {name}.")
        return ("info", f"{name} was already invited.")

    def save(self, *args, **kwargs):
        """Override save to generate a slug from the name."""
        self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        """String representation of the Department model."""
        return self.name

    class Meta:
        """Meta options for the Department model."""
        ordering = ["name"]
