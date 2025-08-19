from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("pages.urls")),
    path("MerchantAcount/", include("MerchantAcount.urls")),
    path("Merchant/", include("Merchant.urls")),
]
