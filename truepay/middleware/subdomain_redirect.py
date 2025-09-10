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

            # 檢查是否訪問了非商店相關的頁面
            restricted_response = self.check_custom_domain_restrictions(request, own_domain.merchant)
            if restricted_response:
                return restricted_response

            if request.path_info == "/":
                request.path_info = "/shop/"
            elif request.path_info.startswith("/pay/"):
                request.path_info = "/shop" + request.path_info
            return None

        except MerchantOwnDomain.DoesNotExist:
            return None

    def check_custom_domain_restrictions(self, request, merchant):
        """
        檢查自訂域名是否訪問了受限制的頁面
        自訂域名只允許訪問商店相關頁面
        """
        path = request.path_info.lower()
        
        # 允許的路徑模式（完整商店功能）
        allowed_patterns = [
            r'^/$',                          # 首頁
            r'^/shop/',                      # 商店相關頁面
            r'^/pay/',                       # 付款頁面
            r'^/customers/login/',           # 客戶登入
            r'^/customers/logout/',          # 客戶登出
            r'^/customers/register/',        # 客戶註冊
            r'^/customers/dashboard/',       # 客戶個人頁面
            r'^/customers/profile/',         # 客戶資料編輯
            r'^/payments/',                  # 付款處理
            r'^/static/',                    # 靜態資源
            r'^/media/',                     # 媒體文件
            r'^/favicon\.ico$',              # 網站圖示
        ]
        
        # 檢查是否符合允許的模式
        for pattern in allowed_patterns:
            if re.match(pattern, path):
                return None  # 允許訪問
        
        # 不允許的頁面（如商家後台）重導向到 localhost:8000
        scheme = "http"  # localhost 使用 HTTP
        original_path = request.get_full_path()
        redirect_url = f"{scheme}://localhost:8000{original_path}"
        return HttpResponseRedirect(redirect_url)
