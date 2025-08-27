from django.contrib import admin
from django.urls import path, include
from merchant_account import views as merchant_views
from django.shortcuts import redirect


def accounts_login_redirect(request):
    """重導向舊的 accounts/login/ 到新的 customers/login/"""
    return redirect("/customers/login/", permanent=True)


from django.shortcuts import redirect
from django.views.generic import RedirectView


def accounts_login_redirect(request):
    """重導向舊的 accounts/login/ 到新的 customers/login/"""
    return redirect("/customers/login/", permanent=True)


urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("pages.urls")),
    path("merchant/", include("merchant_account.urls")),
    path("customers/", include("customers_account.urls")),
    path("marketplace/", include("merchant_marketplace.urls")),
    path("pay/", include("merchant_marketplace.public_urls")),
    path("payments/", include("payments.urls")),
    # 相容性重導向：舊的 accounts/login/ 重導向到新的 customers/login/
    path(
        "accounts/login/",
        RedirectView.as_view(pattern_name="customers_account:login", permanent=True),
    ),
]
