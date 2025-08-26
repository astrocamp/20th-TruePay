from django.urls import path
from . import views

app_name = "merchant_account"

urlpatterns = [
    path("register/", views.register, name="register"),
    path("login/", views.login, name="login"),
    path("logout/", views.logout, name="logout"),
    path("domain_settings/", views.domain_settings, name="domain_settings"),
    path("shop/<slug:subdomain>/", views.shop_overview, name="shop_overview"),
    path("qrscan/", views.qrscan, name="qrscan"),
    path("validate-ticket/", views.validate_ticket, name="validate_ticket"),
    path("use-ticket/", views.use_ticket, name="use_ticket"),
    path("restart-scan/", views.restart_scan, name="restart_scan"),
]
