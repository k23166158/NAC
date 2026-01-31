"""
URL configuration for resolveme project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from tickets.views import HomeView, CustomLoginView, DepartmentView, CreateDepartmentView, TicketThreadView, ForwardTicketView
from django.contrib.auth.views import LogoutView
from tickets.views import SignUpView
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', HomeView.as_view(), name='home'),
    path('login/', CustomLoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('tickets/<uuid:uuid>/', TicketThreadView.as_view(), name='ticket_thread'),
    path('department/<slug:department_slug>/', DepartmentView.as_view(), name='department'),
    path('signup/', SignUpView, name='signup'),
    path('departments/create/', CreateDepartmentView.as_view(), name='create_department'),
    path("tickets/<uuid:ticket_id>/forward/", ForwardTicketView.as_view(), name="ticket_forward"),
]
