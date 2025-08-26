from django.urls import path
from . import views

app_name = "payments"

urlpatterns = [
    # 統一付款入口
    path("create/", views.create_payment, name="create_payment"),
    
    # 付款狀態查詢
    path("status/<uuid:payment_id>/", views.payment_status, name="payment_status"),
    
    # 藍新金流回調
    path("newebpay/return/", views.newebpay_return, name="newebpay_return"),
    path("newebpay/notify/", views.newebpay_notify, name="newebpay_notify"),
    
    # LINE Pay 回調
    path("linepay/confirm/", views.linepay_confirm, name="linepay_confirm"),
    path("linepay/cancel/", views.linepay_cancel, name="linepay_cancel"),
]