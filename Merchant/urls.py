from django.urls import path
from . import views

app_name = "Merchant"

urlpatterns = [
    path("", views.create, name="create"),
    path("new/", views.new, name="new"),
]
