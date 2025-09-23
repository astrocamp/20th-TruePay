import re
import os
import logging
from django.http import HttpResponsePermanentRedirect, HttpResponseRedirect
from django.conf import settings
from merchant_account.models import SubdomainRedirect
from accounts.models import Member
from django.http import Http404
from django.contrib.auth import login


logger = logging.getLogger(__name__)


class SubdomainRedirectMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):

        path_redirect_response = self.check_path_redirect(request)
        if path_redirect_response:
            return path_redirect_response

        # 先檢查舊的子域名重導向（優先級最高）
        redirect_response = self.check_subdomain_redirect(request)
        if redirect_response:
            return redirect_response

        # 再檢查子域名（如 shop1.ushionagisa.work）
        subdomain_response = self.check_truepay_subdomain(request)
        if subdomain_response:
            return subdomain_response

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
            scheme = "https" if request.is_secure() else "http"
            subdomain_url = f"{scheme}://{subdomain}.{base_domain}{redirect_path}"
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
        # 先嘗試從路徑提取子網域
        current_slug, url_type = self.extract_slug_from_path(request)

        # 如果路徑無法提取，從 HTTP_HOST 提取子網域
        if not current_slug:
            host = request.META.get("HTTP_HOST", "").lower()
            if ":" in host:
                host = host.split(":")[0]

            base_domain_with_dot = f".{settings.BASE_DOMAIN}"
            if host.endswith(base_domain_with_dot):
                current_slug = host.removesuffix(base_domain_with_dot)
                if current_slug and current_slug != "www":
                    url_type = "subdomain"

        if not current_slug:
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
        scheme = "https" if request.is_secure() else "http"
        query_string = request.META.get("QUERY_STRING", "")

        if url_type == "subdomain":
            new_host = f"{new_subdomain}.{settings.BASE_DOMAIN}"
            new_url = f"{scheme}://{new_host}{request.path_info}"
        else:
            original_path = request.path_info.strip("/")
            current_slug, _ = self.extract_slug_from_path(request)
            if current_slug:
                new_path = original_path.replace(current_slug, new_subdomain, 1)
            else:
                new_path = original_path
            host = request.META.get("HTTP_HOST", "")
            new_url = f"{scheme}://{host}/{new_path}"

        if query_string:
            new_url += f"?{query_string}"
        return new_url

    def get_client_ip(self, request):
        """獲取客戶端真實 IP"""
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            ip = x_forwarded_for.split(",")[0].strip()
        else:
            ip = request.META.get("REMOTE_ADDR")
        return ip

    def is_internal_request(self, ip):
        """檢查是否為內部請求"""
        internal_ips = [
            "127.0.0.1",
            "localhost",
            "::1",
            "172.17.0.1",  # Docker bridge network
            "172.18.0.1",  # Docker bridge network
            "172.19.0.1",  # Docker bridge network
            "172.20.0.1",  # Docker bridge network
        ]

        # 也檢查是否來自同一個容器網路
        if ip and (ip.startswith("172.") or ip.startswith("10.") or ip == "127.0.0.1"):
            return True

        return ip in internal_ips

    def check_truepay_subdomain(self, request):
        """
        檢查 TruePay 子域名（如 shop1.ushionagisa.work）
        """
        # 手動從 HTTP_HOST 獲取主機名，避免 Django 的 ALLOWED_HOSTS 檢查
        host = request.META.get("HTTP_HOST", "").lower()
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
                    scheme = "https" if request.is_secure() else "http"

                    # 對於登入頁面，需要處理 next 參數
                    if request.path_info.startswith("/customers/login/"):
                        next_param = request.GET.get("next")
                        if next_param and next_param.startswith("/"):
                            next_url = (
                                f"{scheme}://{subdomain}.{main_domain}{next_param}"
                            )
                        elif next_param:
                            next_url = next_param
                        else:
                            next_url = f"{scheme}://{subdomain}.{main_domain}/"
                        redirect_url = (
                            f"{scheme}://{main_domain}/customers/login/?next={next_url}"
                        )
                    else:
                        # 其他認證相關頁面直接重導向到主網域
                        redirect_url = (
                            f"{scheme}://{main_domain}{request.get_full_path()}"
                        )
                    return HttpResponsePermanentRedirect(redirect_url)

                if request.path_info == "/":
                    request.path_info = "/shop/"
                elif request.path_info.startswith("/pay/"):
                    request.path_info = "/shop" + request.path_info

                return None

            except Merchant.DoesNotExist:
                raise Http404("商店不存在")

        return None
