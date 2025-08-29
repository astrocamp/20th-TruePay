from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("pages.urls")),
    path("merchant/", include("merchant_account.urls")),
    path("customers/", include("customers_account.urls")),
    path("marketplace/", include("merchant_marketplace.urls")),
    path("store/", include("public_store.urls")),  # 新的公開商店路由
    path("payments/", include("payments.urls")),
    # 相容性重導向：舊的路由重導向到新的結構
    path(
        "accounts/login/",
        RedirectView.as_view(pattern_name="customers_account:login", permanent=True),
    ),
    path(
        "pay/<int:id>/",
        RedirectView.as_view(pattern_name="public_store:payment_page", permanent=True),
    ),
    path(
        "merchant/shop/<slug:subdomain>/",
        RedirectView.as_view(pattern_name="public_store:shop_overview", permanent=True),
    ),
]
