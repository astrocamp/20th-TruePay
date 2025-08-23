from merchant_account.models import Merchant


class subdomain_middleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # 檢查自訂域名
        host = request.META.get("HTTP_HOST", "").replace("www.", "")

        if (
            not host.endswith("127.0.0.1")
            and not host.endswith("truepay.local")
            and not host.endswith("localhost")
        ):
            try:
                merchant = Merchant.objects.get(
                    merchant_domain=host, use_merchant_domain=True
                )
                request.tenant = merchant
                return self.get_response(request)
            except Merchant.DoesNotExist:
                pass
        # 方式1: 檢查URL參數 ?shop=subdomain (用於測試)
        shop_param = request.GET.get("shop")
        if shop_param:
            try:
                merchant = Merchant.objects.get(subdomain=shop_param)
                request.tenant = merchant
                return self.get_response(request)
            except Merchant.DoesNotExist:
                pass
        # 方式2: 檢查真實subdomain
        host = request.META.get("HTTP_HOST", "")
        subdomain = host.split(".")[0]

        try:
            merchant = Merchant.objects.get(subdomain=subdomain)
            request.tenant = merchant
        except Merchant.DoesNotExist:
            request.tenant = None
        return self.get_response(request)
