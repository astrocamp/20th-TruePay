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


def shop_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        shop_param = request.GET.get("shop")
        shop_id_param = request.GET.get("shop_id")
        if shop_param or shop_id_param:
            try:
                if shop_param:
                    merchant = Merchant.objects.get(subdomain=shop_param)
                else:  # shop_id_param
                    merchant = Merchant.objects.get(id=shop_id_param)

                if (
                    request.user.is_authenticated
                    and request.user.username == f"merchant_{merchant.Email}"
                ):
                    request.merchant = merchant
                    return view_func(request, *args, **kwargs)
                else:
                    return redirect("merchant_account:login")

            except Merchant.DoesNotExist:
                if shop_param:
                    raise Http404(f"找不到子域名為 '{shop_param}' 的商家")
                else:
                    raise Http404(f"找不到ID為 '{shop_id_param}' 的商家")
        else:
            merchant = None
            if request.user.is_authenticated and request.user.username.startswith(
                "merchant_"
            ):
                email = request.user.username.replace("merchant_", "")
                merchant = Merchant.objects.filter(Email=email).first()
                if not merchant:
                    raise Http404("找不到此頁面")

                request.merchant = merchant

                if request.method == "GET":
                    shop_param = merchant.subdomain or merchant.id
                    param_name = "shop" if merchant.subdomain else "shop_id"
                    return redirect(f"{request.path}?{param_name}={shop_param}")
                else:
                    return view_func(request, *args, **kwargs)

    return wrapper
