from django.urls import path
from . import views

app_name = "Merchant"

urlpatterns = [
    path("", views.home, name="home"),
]
