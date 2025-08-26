from django.urls import path
from . import views
from .newebpay import newebpay_return, newebpay_notify
from .linepay import linepay_confirm, linepay_cancel

app_name = "payments"

urlpatterns = [
    # 統一付款入口
    path("create/", views.create_payment, name="create_payment"),
    
    # 付款狀態查詢
    path("status/<int:order_id>/", views.payment_status, name="payment_status"),
    
    # 藍新金流回調
    path("newebpay/return/", newebpay_return, name="newebpay_return"),
    path("newebpay/notify/", newebpay_notify, name="newebpay_notify"),
    
    # LINE Pay 回調
    path("linepay/confirm/", linepay_confirm, name="linepay_confirm"),
    path("linepay/cancel/", linepay_cancel, name="linepay_cancel"),
]