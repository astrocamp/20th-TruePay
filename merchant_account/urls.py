from django.urls import path
from . import views

app_name = "merchant_account"

urlpatterns = [
    path("register/", views.register, name="register"),
    path("login/", views.login, name="login"),
    path("logout/", views.logout, name="logout"),
    # 票券驗證相關路由
    path(
        "ticket/<slug:subdomain>/",
        views.ticket_validation_page,
        name="ticket_validation",
    ),
    path(
        "ticket/validate/<slug:subdomain>/",
        views.validate_ticket,
        name="validate_ticket",
    ),
    path("ticket/use/<slug:subdomain>/", views.use_ticket, name="use_ticket"),
    path(
        "ticket/scan_restart/<slug:subdomain>/", views.restart_scan, name="restart_scan"
    ),
    path(
        "verification_records/<slug:subdomain>/",
        views.verification_records,
        name="verification_records",
    ),
    path("dashboard/<slug:subdomain>/", views.dashboard, name="dashboard"),
    path(
        "subdomain_management/<slug:subdomain>/",
        views.subdomain_management,
        name="subdomain_management",
    ),
    path(
        "transaction_history/<slug:subdomain>/",
        views.transaction_history,
        name="transaction_history",
    ),
    path(
        "profile-settings/<slug:subdomain>/",
        views.profile_settings,
        name="profile_settings",
    ),
    path(
        "own-domains/<slug:subdomain>/",
        views.own_domain_list,
        name="own_domain_list",
    ),
    path(
        "own-domains/add/<slug:subdomain>/",
        views.own_domain_add,
        name="own_domain_add",
    ),
    path(
        "own-domains/detail/<slug:subdomain>/<int:pk>/",
        views.own_domain_detail,
        name="own_domain_detail",
    ),
    # 報表分析相關路由
    path(
        "reports/<slug:subdomain>/",
        views.reports_dashboard,
        name="reports",
    ),
    path(
        "export/sales/<slug:subdomain>/",
        views.export_sales_report,
        name="export_sales",
    ),
    path(
        "export/tickets/<slug:subdomain>/",
        views.export_ticket_report,
        name="export_tickets",
    ),
    path(
        "export/products/<slug:subdomain>/",
        views.export_product_report,
        name="export_products",
    ),
]
