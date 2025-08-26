from merchant_account.models import Merchant
from django.shortcuts import redirect
from django.conf import settings
from merchant_account.views import shop_overview


class subdomain_middleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # 檢查自訂域名（通向商品總覽頁面）
        host = request.META.get("HTTP_HOST", "").replace("www.", "")
        if ":" in host:
            host = host.split(":")[0]
        if (
            not host.endswith("127.0.0.1")
            and not host.endswith("truepay.local")
            and not host.endswith("localhost")
        ):
            try:
                merchant = Merchant.objects.get(
                    merchant_domain=host, use_merchant_domain=True
                )
                return shop_overview(request, merchant.subdomain)
            except Merchant.DoesNotExist:
                if settings.DEBUG:
                    print(f"[DEBUG] 找不到使用自訂域名 '{host}' 的商家")
                pass
        return self.get_response(request)
