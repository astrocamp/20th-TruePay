from django.urls import path
from . import views

app_name = "merchant_account"

urlpatterns = [
    path("register/", views.register, name="register"),
    path("login/", views.login, name="login"),
    path("logout/", views.logout, name="logout"),
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
]
