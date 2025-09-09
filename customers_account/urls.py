from django.urls import path
from . import views

app_name = "customers_account"

urlpatterns = [
    path("register/", views.register, name="register"),
    path("login/", views.login, name="login"),
    path("logout/", views.logout, name="logout"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("purchase-history/", views.purchase_history, name="purchase_history"),
    path("ticket-wallet/", views.ticket_wallet, name="ticket_wallet"),
    path("profile-settings/", views.profile_settings, name="profile_settings"),
    
    # TOTP 二階段驗證相關路由
    path("totp/setup/", views.totp_setup, name="totp_setup"),
    path("totp/enable/", views.totp_enable, name="totp_enable"),
    path("totp/manage/", views.totp_manage, name="totp_manage"),
    path("totp/disable/", views.totp_disable, name="totp_disable"),
    path("totp/regenerate_backup/", views.regenerate_backup_tokens, name="regenerate_backup_tokens"),
    
    # TOTP API
    path("api/totp/verify/", views.verify_totp_api, name="verify_totp_api"),

    path("cancel-order/<int:order_id>/", views.cancel_order, name="cancel_order"),
    path("forgot-password/", views.forgot_password, name="forgot_password"),
    path("reset-password/<str:token>/", views.reset_password, name="reset_password"),
]
