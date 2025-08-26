from django.urls import path
from . import views

app_name = "merchant_account"

urlpatterns = [
    path("register/", views.register, name="register"),
    path("login/", views.login, name="login"),
    path("logout/", views.logout, name="logout"),
    path("domain_settings/", views.domain_settings, name="domain_settings"),
    path("shop/<slug:subdomain>/", views.shop_overview, name="shop_overview"),
]
