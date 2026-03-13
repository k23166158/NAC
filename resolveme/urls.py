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
from tickets.views import (
    HomeView, CustomLoginView, 
    TicketThreadView, ForwardTicketView, CreateTicketView,
    DepartmentView, CreateDepartmentView, DepartmentManageView, EditDepartmentView, DeleteDepartmentView,
    UserManagementView, ToggleUserStatusView, AdminStatisticsView
)
from django.contrib.auth.views import LogoutView
from tickets.views.auth import SignUpView
from tickets.views.profile_view import ProfileView
from tickets.views.profile_edit_view import ProfileEditView
from django.conf import settings
from django.conf.urls.static import static
from tickets.views.notifications_view import NotificationView
from tickets.views.search_assignables_view import search_assignables

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', HomeView.as_view(), name='home'),
    path('login/', CustomLoginView.as_view(), name='login'),
    path('signup/', SignUpView, name='signup'),
    path('logout/', LogoutView.as_view(), name='logout'),

    path('notifications/', NotificationView.as_view(), name='notifications'),
    
    path('tickets/<uuid:uuid>/', TicketThreadView.as_view(), name='ticket_thread'),
    path("tickets/<uuid:ticket_id>/forward/", ForwardTicketView.as_view(), name="ticket_forward"),
    path("tickets/create/", CreateTicketView.as_view(), name="ticket_create"),
    path("ticket/search-assignables/", search_assignables, name="search_assignables"),

    path('department/manage/', DepartmentManageView.as_view(), name='department_manage'),
    path('department/create/', CreateDepartmentView.as_view(), name='create_department'),
    path('department/edit/<slug:department_slug>/', EditDepartmentView.as_view(), name='edit_department'),
    path('department/delete/<slug:department_slug>/', DeleteDepartmentView.as_view(), name='delete_department'),
    path('department/<slug:department_slug>/', DepartmentView.as_view(), name='department'),
    path("tickets/<uuid:ticket_id>/forward/", ForwardTicketView.as_view(), name="ticket_forward"),
    path('manage-users/', UserManagementView.as_view(), name='manage_users'),
    path('manage-users/<int:pk>/toggle-status/', ToggleUserStatusView.as_view(), name='toggle_user_status'),
    path('admin-statistics/', AdminStatisticsView.as_view(), name='admin_statistics'),
    path("profile/edit/", ProfileEditView.as_view(), name="profile_edit"),
    path("profile/<slug:profile_slug>/", ProfileView.as_view(), name="profile"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
