from django.contrib import admin
from django.urls import path, include
from django.shortcuts import redirect

def accounts_login_redirect(request):
    """重導向舊的 accounts/login/ 到新的 customers/login/"""
    return redirect('/customers/login/', permanent=True)

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("pages.urls")),
    path("merchant/", include("merchant_account.urls")),
    path("customers/", include("customers_account.urls")),
    path("marketplace/", include("merchant_marketplace.urls")),
    path("pay/", include("merchant_marketplace.public_urls")),
    path("newebpay/", include("newebpay.urls")),
    # 相容性重導向
    path("accounts/login/", accounts_login_redirect),
    path("orders/", include("orders.urls")),
    path("linepay/", include("linepay.urls", namespace="linepay"))
]
