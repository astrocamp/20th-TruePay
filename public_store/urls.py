from django.urls import path
from . import views

app_name = "public_store"

urlpatterns = [
    path("", views.shop_overview, name="shop_overview"),
    path("pay/<int:id>/", views.payment_page, name="payment_page"),
    path("<slug:subdomain>/", views.shop_overview, name="shop_overview"),
    path("<slug:subdomain>/pay/<int:id>/", views.payment_page, name="payment_page"),
]
