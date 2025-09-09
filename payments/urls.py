from django.urls import path
from . import views
from .newebpay import newebpay_return, newebpay_notify
from .linepay import linepay_confirm, linepay_cancel

app_name = "payments"

urlpatterns = [
    # 統一付款入口
    path("create/", views.create_payment, name="create_payment"),
    
    # 重新付款功能
    path("retry/<int:order_id>/", views.retry_payment, name="retry_payment"),
    
    # 付款狀態查詢
    path("status/<int:order_id>/", views.payment_status, name="payment_status"),
    
    # 訂單限制錯誤頁面
    path("order-limit-error/", views.order_limit_error, name="order_limit_error"),
    
    # TOTP 驗證頁面
    path("totp_verify/", views.totp_verify, name="totp_verify"),
    
    # 藍新金流回調
    path("newebpay/return/", newebpay_return, name="newebpay_return"),
    path("newebpay/notify/", newebpay_notify, name="newebpay_notify"),
    
    # LINE Pay 回調
    path("linepay/confirm/", linepay_confirm, name="linepay_confirm"),
    path("linepay/cancel/", linepay_cancel, name="linepay_cancel"),
]