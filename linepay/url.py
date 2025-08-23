from django.urls import path
from . import views

app_name = "linepay"

urlpatterns = [
    path("reserve/<int:order_id>/", views.reserve, name="reserve"),
    path("confirm/", views.confirm, name="confirm"),
    path("cancel/", views.cancel, name="cancel"),
]
