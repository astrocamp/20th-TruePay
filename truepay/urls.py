from django.contrib import admin
from django.urls import path, include
from debug_toolbar.toolbar import debug_toolbar_urls

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("pages.urls")),
    path("merchant_account/", include("merchant_account.urls")),
    path("Merchant/", include("Merchant.urls")),
    path("", include("pages.urls")),
    path("customers_account/", include("customers_account.urls")),
] + debug_toolbar_urls()
