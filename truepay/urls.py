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
    path("embed/", include("embed_system.urls")),  # 嵌入系統 URLs
    path("i18n/", include("django.conf.urls.i18n")),  # 語言切換
    path("", include("pages.urls")),
]

# 測試錯誤頁面的路由（僅在DEBUG模式下）
if settings.DEBUG:
    from .test_error_views import (
        test_404_view,
        test_500_view,
        test_403_view,
        test_400_view,
        trigger_404_view,
        trigger_500_view,
        trigger_403_view,
        trigger_400_view,
    )

    urlpatterns += [
        path("test/400/", test_400_view, name="test_400"),
        path("test/403/", test_403_view, name="test_403"),
        path("test/404/", test_404_view, name="test_404"),
        path("test/500/", test_500_view, name="test_500"),
        path("test/trigger-400/", trigger_400_view, name="trigger_400"),
        path("test/trigger-403/", trigger_403_view, name="trigger_403"),
        path("test/trigger-404/", trigger_404_view, name="trigger_404"),
        path("test/trigger-500/", trigger_500_view, name="trigger_500"),
    ]

# 自定義錯誤處理器
handler400 = "truepay.error_views.custom_400_view"
handler403 = "truepay.error_views.custom_403_view"
handler404 = "truepay.error_views.custom_404_view"
handler500 = "truepay.error_views.custom_500_view"
