from django.contrib.auth.views import LoginView
from django.contrib.auth import login
from django.shortcuts import redirect, render
from tickets.forms.signup import SignUpForm

class CustomLoginView(LoginView):
    """Custom login view that redirects authenticated users."""
    template_name = 'login.html'
    redirect_authenticated_user = True

def handle_signup_post(request):
    """Handle POST logic for sign up, returns (user, form) tuple."""
    form = SignUpForm(request.POST, request.FILES)
    if form.is_valid():
        user = form.create_active_user()
        login(request, user)
        return user, form
    return None, form

def SignUpView(request):
    """Render the sign-up page. Redirects if authenticated. Handles GET and POST separately."""
    if request.user.is_authenticated:
        return redirect('home')
    if request.method == 'POST':
        user, form = handle_signup_post(request)
        return redirect('home') if user else render(request, 'signup.html', {'form': form})
    return render(request, 'signup.html', {'form': SignUpForm()})
