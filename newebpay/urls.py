from django.urls import path
from . import views

app_name = "newebpay"

urlpatterns = [
    # 建立付款訂單
    path("payment/create/", views.create_payment, name="create_payment"),
    # 查詢付款狀態
    path(
        "payment/status/<uuid:payment_id>/", views.payment_status, name="payment_status"
    ),
    # 藍新金流回調 URL
    path("payment/return/", views.payment_return, name="payment_return"),
    path("payment/notify/", views.payment_notify, name="payment_notify"),
    path("payment/cancel/", views.payment_cancel, name="payment_cancel"),
]
