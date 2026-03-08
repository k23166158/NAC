from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, render
from django.contrib.auth import get_user_model
from django.http import HttpResponseForbidden

from tickets.models import Ticket, TicketMessage
from tickets.models.department import Department
from tickets.models.ticket_department import TicketDepartment
from tickets.models.ticket_message_attachments import TicketMessageAttachment
from tickets.models.ticket_participant import TicketParticipant

User = get_user_model()


class TicketThreadView(LoginRequiredMixin, View):
    """View to display the thread of messages of tickets."""

    class StaffAssignmentHandler:
        """Handler for adding or removing staff assignments to a ticket."""
        def __init__(self, view, action):
            """Initialize the handler with the view and action type."""
            self.view = view
            self.action = action

        def add(self, user, actor):
            """Add a staff user to the ticket."""
            self.view._add_staff(user, actor)

        def remove(self, user):
            """Remove a staff user from the ticket and log the action."""
            self.view._remove_staff(user)

    class DepartmentAssignmentHandler:
        """Handler for adding or removing department assignments to a ticket."""
        def __init__(self, view, action):
            """Initialize the handler with the view and action type."""
            self.view = view
            self.action = action

        def add(self, department, actor):
            """Add a department to the ticket."""
            self.view._add_department(department, actor)

        def remove(self, department):
            """Remove a department to the ticket and log the action."""
            self.view._remove_department(department)

    model = Ticket
    template_name = 'ticket_thread.html'

    def get(self, request, uuid):
        """Handle GET requests: render the ticket thread."""
        self.ticket = get_object_or_404(Ticket, uuid=uuid)
        self.object = self.ticket
        self.ticket.mark_read_for(request.user)
        context = self.get_context_data()
        context["permission"] = self.has_edit_permissions(self.ticket, request.user)
        return render(request, self.template_name, context)

    def post(self, request, uuid):
        """Handle POST actions for the ticket thread."""
        self.ticket = get_object_or_404(Ticket, uuid=uuid)
        self.object = self.ticket
        self.request = request

        if not self.has_edit_permissions(self.object, request.user):
            return HttpResponseForbidden("You don't have permission to do this.")
        action = request.POST.get("action")
        target_type = request.POST.get("target_type")
        if action in {"add", "remove"}:
            return self._handle_add_remove(request, target_type)
        self.dispatch_post_action(action, request)
        return self.get(request, uuid)

    def _handle_add_remove(self, request, target_type):
        """Handle add/remove actions for staff or department assignments."""
        if target_type:
            self.handle_assignment_change(request)
            return self.get(request, self.object.uuid)

        self.handle_staff_change(request)
        return self.get(request, self.object.uuid)
    
    def get_messages_queryset(self):
        """Get the queryset for ticket messages."""
        return (
            TicketMessage.objects
            .filter(ticket=self.object)
            .select_related("sender")
            .prefetch_related("attachments")
            .order_by("created_at")
        )

    def get_first_message(self, messages):
        """Extract the first message."""
        return messages.first()

    def get_reply_messages(self, messages):
        """Extract reply messages (excluding the first)."""
        return messages[1:] if messages.count() > 1 else []

    def get_last_user_message_id(self, messages):
        """Get the ID of the last visible user message."""
        last_user_message = messages.filter(sender=self.request.user).last()
        return last_user_message.id if last_user_message else None

    def get_ticket_staff(self):
        """Get the staff users assigned to the ticket."""
        return self.object.get_ticket_staff()

    def get_department_staff(self):
        """Gets all the staff in a department"""
        return self.object.get_department_staff()

    def has_edit_permissions(self, ticket, user):
        """Check if a user has edit permissions for a ticket"""
        return ticket.can_edit(user)

    def get_available_staff(self, current_staff):
        """Get staff users available to be added to the ticket."""
        current_ids = [u.id for u in current_staff]
        return User.objects.filter(is_staff=True).exclude(id__in=current_ids)

    def get_ticket_departments(self):
        """Get departments assigned to the ticket."""
        return Department.objects.filter(ticket_departments__ticket=self.object)

    def get_available_departments(self, current_departments):
        """Get departments that are not yet assigned to the ticket."""
        current_ids = [d.id for d in current_departments]
        return Department.objects.exclude(id__in=current_ids)

    def get_context_data(self):
        """Add ticket messages to the context."""
        messages = self.get_messages_queryset()
        staff = self.get_ticket_staff()
        departments = self.get_ticket_departments()
        return {
            "ticket": self.object,
            "staff": staff,
            "available_staff": self.get_available_staff(staff),
            "ticket_departments": departments,
            "available_departments": self.get_available_departments(departments),
            "first_message": self.get_first_message(messages),
            "messages": self.get_reply_messages(messages),
            "last_user_message_id": self.get_last_user_message_id(messages),
            "edit_message": self.get_edit_message(),
        }

    def touch_ticket(self):
        """Update the ticket's updated_at timestamp."""
        self.object.touch()

    def get_edit_message(self):
        """Return the message being edited, if any."""
        message_id = self.request.POST.get("message_id")
        if self.request.POST.get("action") == "edit" and message_id:
            return get_object_or_404(
                TicketMessage,
                id=message_id,
                ticket=self.object,
                sender=self.request.user,
                hidden=False,
            )
        return None

    def _save_attachments_for_message(self, request, message):
        """Save any uploaded files as TicketMessageAttachment rows."""
        getlist = getattr(request.FILES, "getlist", None)
        files = (getlist("attachments") + getlist("attachment")) if getlist else []
        files = files or [f for _, f in getattr(request.FILES, "items", lambda: [])()]
        TicketMessageAttachment.create_for_message(self.object, message, files, request.user)

    def handle_delete_action(self, request):
        """Handle deleting a message by hiding it."""
        message_id = request.POST.get("message_id")
        TicketMessage.hide_user_message(self.object, message_id, request.user)

    def handle_update_action(self, request):
        """Handle updating an existing message."""
        message_id = request.POST.get("message_id")
        body = request.POST.get("body")
        message = TicketMessage.update_user_message(self.object, message_id, request.user, body)
        if message:
            remove_ids = request.POST.getlist("remove_attachment_ids")
            TicketMessageAttachment.delete_for_message(message, remove_ids)
            self._save_attachments_for_message(request, message)

    def handle_add_action(self, request):
        """Handle adding a new message (and any attachments)."""
        message = TicketMessage.add_user_message(self.object, request.user, request.POST.get("body"))
        if not message:
            return
        self._save_attachments_for_message(request, message)

    def _add_staff(self, user, added_by):
        """Assign a staff member to the ticket."""
        TicketParticipant.assign_staff(self.object, user, added_by=added_by)

    def _remove_staff(self, user):
        """Remove a staff member from the ticket and log it."""
        TicketParticipant.remove_participant(self.object, user)
        TicketMessage.create_system_message(
            self.object,
            f"{user.get_full_name()} was removed from the ticket.",
        )

    def handle_staff_change(self, request):
        """Handle adding or removing a staff user from the ticket."""
        user_id = request.POST.get("user_id")
        action = request.POST.get("action")
        if not user_id:
            return
        user = get_object_or_404(User, id=user_id, is_staff=True)
        handlers = {
            "add": lambda: self._add_staff(user, request.user),
            "remove": lambda: self._remove_staff(user),
        }
        handler = handlers.get(action)
        if handler:
            handler()

    def dispatch_post_action(self, action, request):
        """Dispatch POST action to the appropriate handler."""
        handlers = {
            "delete": lambda: self.handle_delete_action(request),
            "update": lambda: self.handle_update_action(request),
            "close_ticket": self.handle_close_ticket_action,
            "edit": lambda: None,
        }

        if action in handlers:
            handlers[action]()
            return

        # IMPORTANT: if no explicit action but body exists, add a message
        if (request.POST.get("body") or "").strip():
            self.handle_add_action(request)

    def _add_department(self, department, added_by):
        """Assign a department to the ticket."""
        TicketDepartment.assign_department(self.object, department, added_by=added_by)

    def _remove_department(self, department):
        """Remove a department from the ticket and log it."""
        TicketDepartment.remove_department(self.object, department)

    def get_assignment_target(self, target_type, target_id):
        """Helper method to get the target user or department based on type and ID."""
        if target_type == "staff":
            return get_object_or_404(User, id=target_id, is_staff=True)
        if target_type == "department":
            return get_object_or_404(Department, id=target_id)
        return None

    def apply_assignment_action(self, handler, target, actor):
        """Apply the add or remove action for staff or department assignments."""
        actions = {
            "add": lambda: handler.add(target, actor),
            "remove": lambda: handler.remove(target),
        }
        action = actions.get(handler.action)
        if action:
            action()

    def handle_assignment_change(self, request):
        """Handle adding or removing staff or department assignments based on POST data."""
        target_id = request.POST.get("target_id")
        target_type = request.POST.get("target_type")
        action = request.POST.get("action")
        if not target_id or not target_type or not action:
            return
        handlers = {
            "staff": TicketThreadView.StaffAssignmentHandler,
            "department": TicketThreadView.DepartmentAssignmentHandler,
        }
        if target_type not in handlers: return
        target = self.get_assignment_target(target_type, target_id)
        if target is None: return
        handler = handlers[target_type](self, action)
        self.apply_assignment_action(handler, target, request.user)

    def handle_close_ticket_action(self):
        """Close the ticket."""
        self.ticket.close()
    
