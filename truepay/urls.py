from django.contrib import admin
from django.urls import path, include
from django.conf import settings

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

# 測試錯誤頁面的路由（僅在DEBUG模式下）
if settings.DEBUG:
    from .test_error_views import test_404_view, test_500_view, trigger_404_view, trigger_500_view
    urlpatterns += [
        path("test/404/", test_404_view, name="test_404"),
        path("test/500/", test_500_view, name="test_500"),
        path("test/trigger-404/", trigger_404_view, name="trigger_404"),
        path("test/trigger-500/", trigger_500_view, name="trigger_500"),
    ]

# 自定義錯誤處理器
handler404 = "truepay.error_views.custom_404_view"
handler500 = "truepay.error_views.custom_500_view"
