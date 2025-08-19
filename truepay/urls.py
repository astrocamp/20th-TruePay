from django.contrib import admin
from django.urls import path, include
from debug_toolbar.toolbar import debug_toolbar_urls

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("pages.urls")),
    path("MerchantAcount/", include("MerchantAcount.urls")),
    path("Merchant/", include("Merchant.urls")),
] + debug_toolbar_urls()
