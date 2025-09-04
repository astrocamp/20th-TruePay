from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("pages.urls")),
    path("merchant/", include("merchant_account.urls")),
    path("customers/", include("customers_account.urls")),
    path("marketplace/shop/<slug:subdomain>/", include("merchant_marketplace.urls")),
    path("shop/", include("public_store.urls")),  # 新的公開商店路由
    path("payments/", include("payments.urls")),
    path("accounts/", include("allauth.urls")),  # Django Allauth URLs
]
