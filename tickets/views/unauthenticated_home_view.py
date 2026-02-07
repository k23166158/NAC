from django.shortcuts import render
from django.views import View


class UnauthenticatedHomeView(View):
    """View for the home page for non-authenticated users."""

    def get(self, request):
        """Handle GET request for unauthenticated home page."""
        return render(request, "unauthenticated_home.html")
