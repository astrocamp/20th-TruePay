from django.urls import path
from . import views

app_name = "merchant_account"

urlpatterns = [
    path("session/", views.login, name="session"),
    path("register/", views.register, name="register"),
    path("logout/", views.logout, name="logout"),
]
