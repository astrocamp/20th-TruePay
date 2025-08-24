from django.urls import path
from . import views

app_name = "customers_account"

urlpatterns = [
    path("register/", views.register, name="register"),
    path("login/", views.login, name="login"),
    path("logout/", views.logout, name="logout"),
    path("purchase-history/", views.purchase_history, name="purchase_history"),
]
