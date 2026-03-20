from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.paginator import Paginator
from django.http import HttpResponseForbidden
from django.shortcuts import render
from django.views import View

from tickets.models import Department, Ticket


class DepartmentActiveTicketsView(LoginRequiredMixin, View):
    """List all active tickets for a department with pagination."""

    def get(self, request, department_slug):
        department = Department.get_by_slug_or_404(department_slug)
        if not department.can_view(request.user):
            return HttpResponseForbidden("You are not allowed to access this.")

        active_tickets = department.get_tickets([Ticket.Status.OPEN, Ticket.Status.PENDING])
        paginator = Paginator(active_tickets, 10)
        page = paginator.get_page(request.GET.get("page"))

        return render(request, "department_tickets.html", {
            "department": department,
            "page": page,
            "title": "Active Tickets",
            "empty_message": "No active tickets found.",
        })
