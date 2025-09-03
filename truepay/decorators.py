from functools import wraps
from django.shortcuts import get_object_or_404, redirect
from django.http import Http404
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
                    and request.user.username == f"merchant_{merchant.Email}"
                ):
                    request.merchant = merchant
                else:
                    return redirect("merchant_account:login")
            except Merchant.DoesNotExist:
                raise Http404(f"找不到子域名為 '{subdomain}' 的商家")

        response = view_func(request, *args, **kwargs)
        if hasattr(response, "__setitem__"):
            response["Cache-Control"] = "no-cache, no-store, must-revalidate"
            response["Pragma"] = "no-cache"
            response["Expires"] = "0"

        return response

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
