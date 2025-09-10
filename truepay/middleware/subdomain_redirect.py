import re
import os
import logging
from django.http import HttpResponsePermanentRedirect, HttpResponseRedirect
from django.conf import settings
from merchant_account.models import SubdomainRedirect, MerchantOwnDomain
from django.http import Http404


logger = logging.getLogger(__name__)


class SubdomainRedirectMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):

        path_redirect_response = self.check_path_redirect(request)
        if path_redirect_response:
            return path_redirect_response

        # 檢查自訂域名（如 ushionagisa.work）
        own_domain_response = self.check_own_domain(request)
        if own_domain_response:
            return own_domain_response

        # 檢查子域名（如 shop1.ushionagisa.work）
        subdomain_response = self.check_truepay_subdomain(request)
        if subdomain_response:
            return subdomain_response

        # 檢查舊的子域名重導向
        redirect_response = self.check_subdomain_redirect(request)
        if redirect_response:
            return redirect_response

        response = self.get_response(request)
        return response

    def check_path_redirect(self, request):
        """
        檢查路徑式訪問並重導向到子網域
        /shop/subdomain/ -> https://subdomain.ushionagisa.work/
        /shop/subdomain/pay/id/ -> https://subdomain.ushionagisa.work/pay/id/
        """
        path = request.path_info.strip("/")
        base_domain = os.getenv("NGROK_URL", settings.BASE_DOMAIN)

        subdomain = None
        redirect_path = "/"

        # 檢查商店首頁路徑：/shop/subdomain/
        shop_match = re.match(r"^shop/([^/]+)/?$", path)
        if shop_match:
            subdomain = shop_match.group(1)

        # 檢查付款頁面路徑：/shop/subdomain/pay/id/
        payment_match = re.match(r"^shop/([^/]+)/pay/(\d+)/?$", path)
        if payment_match:
            subdomain = payment_match.group(1)
            product_id = payment_match.group(2)
        if subdomain:
            subdomain_url = f"https://{subdomain}.{base_domain}{redirect_path}"
            query_string = request.META.get("QUERY_STRING")
            if query_string:
                subdomain_url += f"?{query_string}"
            return HttpResponsePermanentRedirect(subdomain_url)

        return None

    def extract_slug_from_path(self, request):
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
        current_slug, url_type = self.extract_slug_from_path(request)
        if not current_slug or not url_type:
            return None
        try:
            redirect = SubdomainRedirect.objects.select_related("merchant").get(
                old_subdomain=current_slug, is_active=True
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
            logger.error(
                f"Unexpected error during subdomain redirect check for slug '{current_slug}': {e}",
                exc_info=True,
            )
            return None

    def build_redirect_url(self, request, new_subdomain, url_type):
        original_path = request.path_info.strip("/")

        current_slug, _ = self.extract_slug_from_path(request)
        if current_slug:
            new_path = original_path.replace(current_slug, new_subdomain, 1)
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

            # 檢查是否訪問了非商店相關的頁面
            restricted_response = self.check_custom_domain_restrictions(request)
            if restricted_response:
                return restricted_response

            if request.path_info == "/":
                request.path_info = "/shop/"
            elif request.path_info.startswith("/pay/"):
                request.path_info = "/shop" + request.path_info
            return None

        except MerchantOwnDomain.DoesNotExist:
            return None

    def check_custom_domain_restrictions(self, request):
        """
        檢查自訂域名是否訪問了受限制的頁面
        自訂域名只允許訪問商店相關頁面
        """
        path = request.path_info.lower()
        allowed_patterns = [
            r"^/$",
            r"^/shop/",
            r"^/pay/",
            r"^/customers/",
            r"^/payments/",
            r"^/static/",
            r"^/media/",
            r"^/favicon\.ico$",
        ]
        if any(re.match(pattern, path) for pattern in allowed_patterns):
            return None

        scheme = "http" if request.is_secure() else "http"
        base_domain = os.getenv("NGROK_URL", settings.BASE_DOMAIN)
        redirect_url = f"{scheme}://{base_domain}/"
        return HttpResponseRedirect(redirect_url)

    def check_truepay_subdomain(self, request):
        """
        檢查 TruePay 子域名（如 shop1.ushionagisa.work）
        """
        host = request.get_host().lower()
        if ":" in host:
            host = host.split(":")[0]

        base_domain_with_dot = f".{settings.BASE_DOMAIN}"

        if host.endswith(base_domain_with_dot):
            subdomain = host.removesuffix(base_domain_with_dot)
            from merchant_account.models import Merchant

            try:
                merchant = Merchant.objects.get(subdomain=subdomain)
                request.merchant = merchant
                request.domain_type = "truepay_subdomain"

                redirect_to_main_paths = [
                    "/customers/login/",
                    "/selectrole/",
                    "/customers/register/",
                    "/merchant/register/",
                    "/merchant/login/",
                    "/about/",
                    "/contact/",
                    "/pricing/",
                    "/help/",
                    "/merchant/dashboard/",
                    "/merchant/",
                    "/admin/",
                ]
                if any(
                    request.path_info.startswith(path)
                    for path in redirect_to_main_paths
                ):
                    main_domain = os.getenv("NGROK_URL", settings.BASE_DOMAIN)

                    # 對於登入頁面，需要處理 next 參數
                    if request.path_info.startswith("/customers/login/"):
                        next_param = request.GET.get("next")
                        if next_param and next_param.startswith("/"):
                            next_url = f"https://{subdomain}.{main_domain}{next_param}"
                        elif next_param:
                            next_url = next_param
                        else:
                            next_url = f"https://{subdomain}.{main_domain}/"

                        redirect_url = (
                            f"https://{main_domain}/customers/login/?next={next_url}"
                        )
                    else:
                        # 其他認證相關頁面直接重導向到主網域
                        redirect_url = f"https://{main_domain}{request.get_full_path()}"

                    return HttpResponsePermanentRedirect(redirect_url)

                if request.path_info == "/":
                    request.path_info = "/shop/"
                elif request.path_info.startswith("/pay/"):
                    request.path_info = "/shop" + request.path_info

                return None  # 繼續處理請求

            except Merchant.DoesNotExist:
                raise Http404("商店不存在")

        return None
