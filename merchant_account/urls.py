from django.urls import path
from . import views

app_name = "merchant_account"

urlpatterns = [
    path("register/", views.register, name="register"),
    path("login/", views.login, name="login"),
    path("logout/", views.logout, name="logout"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("domain_settings/", views.domain_settings, name="domain_settings"),
    path("transaction_history/", views.transaction_history, name="transaction_history"),
    
    # 票券驗證相關路由
    path("ticket/<slug:subdomain>/", views.ticket_validation_page, name="ticket_validation"),
    path("ticket/validate/<slug:subdomain>/", views.validate_ticket, name="validate_ticket"),
    path("ticket/use/<slug:subdomain>/", views.use_ticket, name="use_ticket"),
    path("ticket/scan_restart/<slug:subdomain>/", views.restart_scan, name="restart_scan"),
    path("dashboard/<slug:subdomain>/", views.dashboard, name="dashboard"),
    path(
        "domain_settings/<slug:subdomain>/",
        views.domain_settings,
        name="domain_settings",
    ),
    path(
        "transaction_history/<slug:subdomain>/",
        views.transaction_history,
        name="transaction_history",
    ),
    path(
        "profile-settings/<slug:subdomain>/",
        views.profile_settings,
        name="profile_settings",
    ),
]
