import re
from django.http import HttpResponsePermanentRedirect, HttpResponseRedirect
from django.utils import timezone
from merchant_account.models import SubdomainRedirect, MerchantOwnDomain


class SubdomainRedirectMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):

        own_domain_response = self.check_own_domain(request)
        if own_domain_response:
            return own_domain_response

        redirect_response = self.check_subdomain_redirect(request)
        if redirect_response:
            return redirect_response

        response = self.get_response(request)
        return response

    def extract_subdomain_from_path(self, request):
        path = request.path_info.strip("/")
        patterns = [
            (r"^merchant/dashboard/([^/]+)/?", "merchant_dashboard"),
            (r"^merchant/transaction_history/([^/]+)/?", "merchant_transaction"),
            (r"^merchant/([^/]+)/([^/]+)/?", "merchant_general"),
            (r"^shop/([^/]+)/?", "shop"),
        ]
        for pattern, url_type in patterns:
            match = re.match(pattern, path)
            if match:
                if url_type == "merchant_general":
                    return match.group(2), url_type
                else:
                    return match.group(1), url_type
        return None, None

    def check_subdomain_redirect(self, request):
        current_subdomain, url_type = self.extract_subdomain_from_path(request)
        if not current_subdomain or not url_type:
            return None
        try:
            redirect = SubdomainRedirect.objects.select_related("merchant").get(
                old_subdomain=current_subdomain, is_active=True
            )
            if not redirect.is_valid():
                redirect.is_active = False
                redirect.save(update_fields=["is_active"])
                return None
            new_url = self.build_redirect_url(request, redirect.new_subdomain, url_type)
            redirect.use_redirect()
            if redirect.redirect_type == "301":
                return HttpResponsePermanentRedirect(new_url)
            else:
                return HttpResponseRedirect(new_url)
        except SubdomainRedirect.DoesNotExist:
            return None
        except Exception as e:
            return None

    def build_redirect_url(self, request, new_subdomain, url_type):
        original_path = request.path_info.strip("/")

        current_subdomain, _ = self.extract_subdomain_from_path(request)
        if current_subdomain:
            new_path = original_path.replace(current_subdomain, new_subdomain, 1)
        else:
            new_path = original_path

        scheme = "https" if request.is_secure() else "http"
        host = request.get_host()
        query_string = request.META.get("QUERY_STRING", "")
        new_url = f"{scheme}://{host}/{new_path}"
        if query_string:
            new_url += f"?{query_string}"
        return new_url

    def check_own_domain(self, request):
        host = request.get_host().lower()
        if ":" in host:
            host = host.split(":")[0]
        try:
            own_domain = MerchantOwnDomain.objects.select_related("merchant").get(
                domain_name=host, is_verified=True, is_active=True
            )
            request.merchant = own_domain.merchant
            request.domain_type = "own_domain"

            if request.path_info == "/":
                request.path_info = "/shop/"
            elif request.path_info.startswith("/pay/"):
                request.path_info = "/shop" + request.path_info
            return None

        except MerchantOwnDomain.DoesNotExist:
            return None
