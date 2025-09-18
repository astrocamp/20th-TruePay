from functools import wraps
from django.shortcuts import get_object_or_404, redirect
from django.http import Http404, HttpResponse
from merchant_account.models import Merchant
from django.views.decorators.cache import never_cache
from django.contrib.auth.decorators import login_required


def no_cache_required(view_func):
    @wraps(view_func)
    @never_cache
    def _wrapped_view(request, *args, **kwargs):
        subdomain = kwargs.get("subdomain")
        if subdomain:
            try:
                merchant = Merchant.objects.get(subdomain=subdomain)
                if (
                    request.user.is_authenticated
                    and request.user.email == merchant.member.email
                    and request.user.member_type == "merchant"
                ):
                    request.merchant = merchant
                else:
                    return redirect("merchant_account:login")
            except Merchant.DoesNotExist:
                raise Http404(f"找不到子域名為 '{subdomain}' 的商家")

        return view_func(request, *args, **kwargs)

    return _wrapped_view


def customer_login_required(view_func):
    @wraps(view_func)
    @login_required(login_url="/customers/login/")
    @never_cache
    def _wrapped_view(request, *args, **kwargs):
        # 設定防快取 headers
        response = view_func(request, *args, **kwargs)
        if hasattr(response, "__setitem__"):
            response["Cache-Control"] = "no-cache, no-store, must-revalidate"
            response["Pragma"] = "no-cache"
            response["Expires"] = "0"

        return response

    return _wrapped_view


def merchant_verified_required(view_func):
    """要求商家通過認證才能執行的裝飾器"""
    @wraps(view_func)
    @no_cache_required
    def _wrapped_view(request, *args, **kwargs):
        # 檢查商家是否可以營業
        if not request.merchant.can_operate():
            # 根據不同狀態生成不同的提示訊息
            if request.merchant.verification_status == "pending" or request.merchant.verification_status == "rejected":
                alert_message = f"商家審核未通過，{request.merchant.rejection_reason}，請到設定頁面填寫完整資料"
            elif request.merchant.verification_status == "suspended":
                alert_message = "商家帳號已被暫停"
            else:
                alert_message = "商家帳號狀態異常，請聯絡客服"

            # 返回帶有 alert 和自動重導向的頁面
            dashboard_url = f"/merchant/dashboard/{request.merchant.subdomain}/"
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>權限不足</title>
                <meta charset="UTF-8">
            </head>
            <body>
                <script>
                    alert("{alert_message}");
                    window.location.href = "{dashboard_url}";
                </script>
            </body>
            </html>
            """
            return HttpResponse(html_content)

        return view_func(request, *args, **kwargs)
    return _wrapped_view
