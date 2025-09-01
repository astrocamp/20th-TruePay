from django.urls import path
from . import views

app_name = "merchant_account"

urlpatterns = [
    path("register/", views.register, name="register"),
    path("login/", views.login, name="login"),
    path("logout/", views.logout, name="logout"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("domain_settings/", views.domain_settings, name="domain_settings"),
    path("transaction_history/", views.transaction_history, name="transaction_history"),
    
    # 票券驗證相關路由
    path("ticket/validate/", views.validate_ticket, name="validate_ticket"),
    path("ticket/use/", views.use_ticket, name="use_ticket"),
    path("ticket/scan_restart/", views.restart_scan, name="restart_scan"),
]
