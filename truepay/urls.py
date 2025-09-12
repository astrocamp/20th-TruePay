from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path("admin/", admin.site.urls),
    path("merchant/", include("merchant_account.urls")),
    path("customers/", include("customers_account.urls")),
    path("marketplace/shop/<slug:subdomain>/", include("merchant_marketplace.urls")),
    path("shop/", include("public_store.urls")),
    path("payments/", include("payments.urls")),
    path("accounts/", include("allauth.urls")),  # Django Allauth URLs
    path("", include("pages.urls")),
]
