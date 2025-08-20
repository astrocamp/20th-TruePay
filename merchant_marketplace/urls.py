from django.urls import path
from . import views

app_name = "merchant_marketplace"

urlpatterns = [
    path("", views.index, name="index"),
    path("new/", views.new, name="new"),
    path("<int:id>/", views.detail, name="detail"),
    path("<int:id>/edit", views.edit, name="edit"),
]
