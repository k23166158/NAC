from django.shortcuts import render
from django.views import View

class HomeView(View):
    """View for the home page that renders different templates based on authentication."""

    def get(self, request):
        """Handle GET requests to the home page."""
        if request.user.is_authenticated:
            return render(request, 'home.html')
        else:
            return render(request, 'landing.html')
