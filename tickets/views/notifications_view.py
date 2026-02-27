from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render


class NotificationView(LoginRequiredMixin, View):
    template_name = "notifications.html"

    def get(self, request):
        return render(request, self.template_name)
