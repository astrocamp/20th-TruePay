from django.urls import path
from . import views

app_name = "public_marketplace"

urlpatterns = [
    path("<int:id>/", views.payment_page, name="payment_page"),
]