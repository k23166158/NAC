from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404

from tickets.models import Ticket, TicketMessage
from tickets.models.department import Department
from tickets.models.ticket_department import TicketDepartment
from tickets.models.ticket_message_attachments import TicketMessageAttachment
from tickets.models.ticket_participant import TicketParticipant


User = get_user_model()


class TicketThreadContextMixin:
    """Provide ticket thread context and message helpers."""

    model = Ticket

    def get_messages_queryset(self):
        """Return ordered messages queryset for the current ticket."""
        return (
            TicketMessage.objects.filter(ticket=self.object)
            .select_related("sender")
            .prefetch_related("attachments")
            .order_by("created_at")
        )

    def get_first_message(self, messages):
        """Return the first message from a queryset."""
        return messages.first()

    def get_reply_messages(self, messages):
        """Return reply messages, excluding the first."""
        return messages[1:] if messages.count() > 1 else []

    def get_last_user_message_id(self, messages):
        """Return ID of the last visible message from the current user."""
        last_message = messages.filter(sender=self.request.user, hidden=False).last()
        return last_message.id if last_message else None

    def get_ticket_staff(self):
        """Return staff users assigned to the current ticket."""
        return self.object.get_ticket_staff()

    def get_department_staff(self):
        """Return staff users from departments assigned to the ticket."""
        return self.object.get_department_staff()

    def get_available_staff(self, current_staff):
        """Return staff eligible to be added to the ticket."""
        current_ids = [u.id for u in current_staff]
        return User.objects.filter(is_staff=True).exclude(id__in=current_ids)

    def get_ticket_departments(self):
        """Return departments currently assigned to the ticket."""
        return Department.objects.filter(ticket_departments__ticket=self.object)

    def get_available_departments(self, current_departments):
        """Return departments that may be assigned to the ticket."""
        current_ids = [d.id for d in current_departments]
        return Department.objects.exclude(id__in=current_ids)

    def user_has_removed_themselves(self, user):
        """Return whether the user has removed themselves from this ticket."""
        return TicketParticipant.objects.filter(
            ticket=self.object,
            user=user,
            removed_self=True,
        ).exists()

    def get_edit_message(self):
        """Return the message being edited, or None."""
        action = self.request.POST.get("action")
        message_id = self.request.POST.get("message_id")
        if action != "edit" or not message_id:
            return None
        return get_object_or_404(
            TicketMessage,
            id=message_id,
            ticket=self.object,
            sender=self.request.user,
            hidden=False,
        )

    def touch_ticket(self):
        """Update the ticket's timestamp."""
        self.object.touch()

    def _save_attachments_for_message(self, request, message):
        """Persist uploaded files as TicketMessageAttachment rows."""
        files = request.FILES.getlist("attachments") + request.FILES.getlist("attachment")
        TicketMessageAttachment.create_for_message(self.object, message, files, request.user)

    def handle_delete_action(self, request):
        """Handle delete action for a user message."""
        message_id = request.POST.get("message_id")
        get_object_or_404(TicketMessage, id=message_id, ticket=self.object, sender=request.user)
        TicketMessage.hide_user_message(self.object, message_id, request.user)

    def _update_message_body(self, request):
        """Return updated message instance for valid update body."""
        message_id = request.POST.get("message_id")
        get_object_or_404(TicketMessage, id=message_id, ticket=self.object, sender=request.user)
        body = request.POST.get("body", "")
        if not body or body.isspace():
            return None
        return TicketMessage.update_user_message(self.object, message_id, request.user, body)

    def handle_update_action(self, request):
        """Handle updating an existing message and its attachments."""
        message = self._update_message_body(request)
        if not message:
            return
        remove_ids = request.POST.getlist("remove_attachment_ids")
        TicketMessageAttachment.delete_for_message(message, remove_ids)
        self._save_attachments_for_message(request, message)

    def _create_message_from_body(self, request):
        """Create a message from POST body and return it."""
        body = request.POST.get("body", "")
        if body and not body.isspace():
            return TicketMessage.add_user_message(self.object, request.user, body)
        return None

    def handle_add_action(self, request):
        """Handle adding a new reply message and attachments."""
        message = self._create_message_from_body(request)
        if not message:
            return
        self._save_attachments_for_message(request, message)

    def dispatch_post_action(self, action, request):
        """Dispatch POST action to the correct handler."""
        handlers = {
            "delete": lambda: self.handle_delete_action(request),
            "update": lambda: self.handle_update_action(request),
            "close_ticket": self.handle_close_ticket_action,
            "edit": lambda: None,
        }
        if action in handlers:
            handlers[action]()
            return
        self.handle_add_action(request)

    def handle_close_ticket_action(self):
        """Close the ticket instance associated with the view."""
        self.ticket.close()


class TicketThreadAssignmentMixin:
    """Provide staff and department assignment helpers."""

    class StaffAssignmentHandler:
        """Handle staff assignment actions."""

        def __init__(self, view, action):
            """Initialise handler with view and action."""
            self.view = view
            self.action = action

        def add(self, user, actor):
            """Add a staff user to the ticket."""
            self.view._add_staff(user, actor)

        def remove(self, user, actor):
            """Remove a staff user from the ticket."""
            self.view._remove_staff(user, actor)

    class DepartmentAssignmentHandler:
        """Handle department assignment actions."""

        def __init__(self, view, action):
            """Initialise handler with view and action."""
            self.view = view
            self.action = action

        def add(self, department, actor):
            """Add a department to the ticket."""
            self.view._add_department(department, actor)

        def remove(self, department, actor):
            """Remove a department from the ticket."""
            self.view._remove_department(department)

    def _add_department(self, department, added_by):
        """Assign a department to the ticket."""
        TicketDepartment.assign_department(self.object, department, added_by=added_by)

    def _remove_department(self, department):
        """Remove a department from the ticket."""
        TicketDepartment.remove_department(self.object, department)

    def _add_staff(self, user, added_by):
        """Assign a staff user to the ticket."""
        TicketParticipant.assign_staff(self.object, user, added_by=added_by)

    def _remove_staff(self, user, removed_by):
        """Remove staff from ticket and record a system message."""
        if user == removed_by:
            participant = TicketParticipant.objects.get(ticket=self.object, user=user)
            participant.removed_self = True
            participant.save()
        else:
            TicketParticipant.remove_participant(self.object, user)
        message = f"{user.get_full_name()} was removed from the ticket."
        TicketMessage.create_system_message(self.object, message)

    def handle_staff_change(self, request):
        """Handle legacy add/remove operations using user_id."""
        user_id = request.POST.get("user_id")
        action = request.POST.get("action")
        if not user_id:
            return
        user = get_object_or_404(User, id=user_id, is_staff=True)
        handlers = {
            "add": lambda: self._add_staff(user, request.user),
            "remove": lambda: self._remove_staff(user, request.user),
        }
        handler = handlers.get(action)
        if handler:
            handler()

    def _assignment_handlers(self):
        """Return mapping of assignment handlers by target type."""
        view_cls = type(self)
        return {
            "staff": view_cls.StaffAssignmentHandler,
            "department": view_cls.DepartmentAssignmentHandler,
        }

    def get_assignment_target(self, target_type, target_id):
        """Return target object for staff or department assignment."""
        if target_type == "staff":
            return get_object_or_404(User, id=target_id, is_staff=True)
        if target_type == "department":
            return get_object_or_404(Department, id=target_id)
        return None

    def apply_assignment_action(self, handler, target, actor):
        """Apply add or remove action to a handler."""
        actions = {
            "add": lambda: handler.add(target, actor),
            "remove": lambda: handler.remove(target, actor),
        }
        action = actions.get(getattr(handler, "action", None))
        if action:
            action()

    def _has_assignment_fields(self, data):
        """Return whether assignment POST data is complete."""
        return all(data.get(key) for key in ("target_id", "target_type", "action"))

    def handle_assignment_change(self, request):
        """Handle staff or department assignment from POST data."""
        data = request.POST
        if not self._has_assignment_fields(data):
            return
        handlers = self._assignment_handlers()
        handler_class = handlers.get(data.get("target_type"))
        if not handler_class:
            return
        target = self.get_assignment_target(data["target_type"], data["target_id"])
        handler = handler_class(self, data["action"])
        self.apply_assignment_action(handler, target, request.user)