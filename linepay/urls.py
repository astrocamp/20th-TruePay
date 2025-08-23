from django.urls import path
from . import views

app_name = "linepay"

urlpatterns = [
    path("reserve/<int:order_id>/", views.reserve, name="linepay_reserve"),
    path("confirm/", views.confirm, name="linepay_confirm"),
    path("cancel/", views.cancel, name="linepay_cancel"),
    path("success/", views.success, name="linepay_success"),
    path("canceled/", views.canceled, name="linepay_canceled"),
    path("create/", views.create_order_and_pay, name="create_order_and_pay"),
]