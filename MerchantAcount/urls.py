from django.urls import path
from . import views

app_name = "MerchantAcount"

urlpatterns = [
    path("session/", views.session, name="session"),
    path("register/", views.register, name="register"),
]
