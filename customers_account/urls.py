from django.urls import path
from . import views

app_name = "customers_account"

urlpatterns = [
    path("customers_register/", views.customer_register, name="register"),
    path("customers_login/", views.customer_login, name="login"),
    path("customers_logout/", views.customer_logout, name="logout"),
]
