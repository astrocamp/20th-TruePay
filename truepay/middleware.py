from merchant_account.models import Merchant


class subdomain_middleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        host = request.META.get("HTTP_HOST", "")
        subdomain = host.split(".")[0]

        try:
            merchant = Merchant.objects.get(subdomain=subdomain)
            request.tenant = merchant
        except Merchant.DoesNotExist:
            request.tenant = None
        return self.get_response(request)
