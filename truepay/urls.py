from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("pages.urls")),
    path("merchant/", include("merchant_account.urls")),
    path("customers/", include("customers_account.urls")),
    path("marketplace/", include("merchant_marketplace.urls")),
    path("pay/", include("merchant_marketplace.public_urls")),
    path("newebpay/", include("newebpay.urls")),
    path("linepay/", include("linepay.urls", namespace="linepay"))
]
