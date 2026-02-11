from django.views.generic import DetailView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404
from django.contrib.auth import get_user_model
from django.utils import timezone
from tickets.helpers.ticket_assignment import assign_staff_to_ticket


from tickets.models.ticket_participant import TicketParticipant
from ..models import Ticket, TicketMessage
from ..models.ticket_department import TicketDepartment
from ..models.department import Department
from tickets.helpers.ticket_assignment import assign_department_to_ticket
from django.http import Http404
from django.test import RequestFactory

User = get_user_model()

class TicketThreadView(LoginRequiredMixin, DetailView):
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
            """Remove a department from the ticket and log the action."""
            self.view._remove_department(department)

    model = Ticket
    template_name = 'ticket_thread.html'
    context_object_name = 'ticket'
    slug_url_kwarg = 'uuid'
    slug_field = 'uuid'

    def get_messages_queryset(self):
        """Get the queryset for ticket messages."""
        return TicketMessage.objects.filter(ticket=self.object).order_by("created_at")

    def get_first_message(self, messages):
        """Extract the first message."""
        return messages.first()

    def get_reply_messages(self, messages):
        """Extract reply messages (excluding the first)."""
        return messages[1:] if messages.count() > 1 else []

    def get_last_user_message_id(self, messages):
        """Get the ID of the last visible user message."""
        last_user_message = messages.filter(sender=self.request.user, hidden=False).last()
        return last_user_message.id if last_user_message else None
    
    def get_ticket_staff(self):
        """Get the staff users assigned to the ticket."""
        return [
            p.user for p in self.object.participants.select_related("user")
        ]

    def get_available_staff(self, current_staff):
        """Get staff users available to be added to the ticket."""
        current_ids = [u.id for u in current_staff]
        return User.objects.filter(is_staff=True).exclude(id__in=current_ids)


    def get_context_data(self, **kwargs):
        """Add ticket messages to the context."""
        context = super().get_context_data(**kwargs)
        messages = self.get_messages_queryset()
        current_staff = self.get_ticket_staff()
        context["staff"] = current_staff
        context["available_staff"] = self.get_available_staff(current_staff)
        context["first_message"] = self.get_first_message(messages)
        context["messages"] = self.get_reply_messages(messages)
        context["last_user_message_id"] = self.get_last_user_message_id(messages)
        context["edit_message"] = self.get_edit_message()
        context["ticket_departments"] = Department.objects.filter(ticket_departments__ticket=self.object)
        context["available_departments"] = Department.objects.exclude(ticket_departments__ticket=self.object)
        return context
    
    def touch_ticket(self):
        """Update the ticket's updated_at timestamp."""
        Ticket.objects.filter(id=self.object.id).update(updated_at=timezone.now())

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

    def handle_delete_action(self, request):
        """Handle deleting a message by hiding it."""
        message_id = request.POST.get("message_id")
        message = get_object_or_404(
            TicketMessage,
            id=message_id,
            ticket=self.object,
            sender=request.user,  # security: only delete own messages
        )
        message.hidden = True
        message.save()
        self.touch_ticket()

    def handle_update_action(self, request):
        """Handle updating an existing message."""
        message_id = request.POST.get("message_id")
        message = get_object_or_404(
            TicketMessage,
            id=message_id,
            ticket=self.object,
            sender=request.user,
            hidden=False,
        )
        body = request.POST.get("body")
        if body:
            message.body = body
            message.edited = True
            message.save()
            self.touch_ticket()

    def handle_add_action(self, request):
        """Handle adding a new message."""
        body = request.POST.get('body')
        if body:
            TicketMessage.objects.create(
                ticket=self.object,
                sender=request.user,
                body=body
            )
            self.touch_ticket()

    def _add_staff(self, user, added_by):
        """Assign a staff member to the ticket."""
        assign_staff_to_ticket(ticket=self.object, staff_user=user, added_by=added_by)

    def _remove_staff(self, user):
        """Remove a staff member from the ticket and log it."""
        TicketParticipant.objects.filter(ticket=self.object, user=user).delete()
        TicketMessage.objects.create(
            ticket=self.object,
            sender=None,
            body=f"{user.get_full_name()} was removed from the ticket."
        )

    def handle_staff_change(self, request):
        """Handle adding or removing a staff user from the ticket."""
        user_id = request.POST.get("user_id")
        action = request.POST.get("action")
        if not user_id: return
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
        handlers.get(action, lambda: self.handle_add_action(request))()

    def post(self, request, *args, **kwargs):
        """Handle POST actions for the ticket thread."""
        self.object = self.get_object()
        action = request.POST.get("action")

        if action in {"add", "remove"}:
            self.handle_assignment_change(request)
            return self.get(request, *args, **kwargs)

        self.dispatch_post_action(action, request)
        return self.get(request, *args, **kwargs)
    
    def _add_department(self, department, added_by):
        """Assign a department to the ticket."""
        assign_department_to_ticket(
            ticket=self.object,
            department=department,
            added_by=added_by,
        )
    
    def _remove_department(self, department):
        """Remove a department from the ticket and log it."""
        TicketDepartment.objects.filter(
            ticket=self.object,
            department=department
        ).delete()

        TicketMessage.objects.create(
            ticket=self.object,
            sender=None,
            body=f"{department.name} was removed from the ticket."
        )

    def get_assignment_target(self, target_type, target_id):
        """Helper method to get the target user or department based on type and ID."""
        if target_type == "staff":
            return get_object_or_404(User, id=target_id, is_staff=True)
        if target_type == "department":
            return get_object_or_404(Department, id=target_id)
    
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
        if not target_id or not target_type or not action: return
        
        target = self.get_assignment_target(target_type, target_id)
        handler = {
            "staff": TicketThreadView.StaffAssignmentHandler,
            "department": TicketThreadView.DepartmentAssignmentHandler,
        }[target_type](self, action)

        self.apply_assignment_action(handler, target, request.user)

    def handle_close_ticket_action(self):
        """Close the ticket."""
        if self.object.status != Ticket.Status.CLOSED:
            self.object.status = Ticket.Status.CLOSED
            self.object.closed_at = timezone.now()
            self.object.save()
            self.touch_ticket()
