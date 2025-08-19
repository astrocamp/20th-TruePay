from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("pages.urls")),
    path("merchant_account/", include("merchant_account.urls")),
    path("merchant/", include("merchant.urls")),
    path("customers_account/", include("customers_account.urls")),
] + debug_toolbar_urls()
