from django.urls import path

from .views import LoginView, LogoutView, MeView, RefreshView, RegisterView, PasswordResetRequestView, PasswordResetConfirmView
from apps.core.views import AdminDashboardView

urlpatterns = [
    path("register/", RegisterView.as_view(), name="auth-register"),
    path("login/", LoginView.as_view(), name="auth-login"),
    path("refresh/", RefreshView.as_view(), name="auth-refresh"),
    path("logout/", LogoutView.as_view(), name="auth-logout"),
    path("me/", MeView.as_view(), name="auth-me"),
    path("password-reset/", PasswordResetRequestView.as_view(), name="auth-password-reset"),
    path("password-reset/confirm/", PasswordResetConfirmView.as_view(), name="auth-password-reset-confirm"),
    path("admin-stats/", AdminDashboardView.as_view(), name="admin-stats"),
]
