from django.contrib import admin
from django.urls import path, include
from merchant_account import views as merchant_views

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("pages.urls")),
    path("merchant/", include("merchant_account.urls")),
    path("customers/", include("customers_account.urls")),
    path("marketplace/", include("merchant_marketplace.urls")),
    path("pay/", include("merchant_marketplace.public_urls")),
    path("newebpay/", include("newebpay.urls")),
    path("linepay/", include("linepay.urls", namespace="linepay")),
    path("shop/<slug:subdomain>/", merchant_views.shop_overview, name="shop_overview"),
]
