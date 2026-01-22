from django.contrib.auth.views import LoginView
from django.shortcuts import redirect

class CustomLoginView(LoginView):
    """Custom login view that redirects authenticated users."""
    template_name = 'login.html'
    redirect_authenticated_user = True