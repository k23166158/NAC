from django.contrib import admin
from .models import Ticket, User, TicketMessage, Department

admin.site.register(User)
admin.site.register(Ticket)
admin.site.register(TicketMessage)
admin.site.register(Department)
