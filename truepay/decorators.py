from functools import wraps
from django.shortcuts import get_object_or_404, redirect
from django.http import Http404
from merchant_account.models import Merchant
from django.contrib import messages
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
        if shop_param:
            try:
                merchant = Merchant.objects.get(subdomain=shop_param)
                merchant_id = request.session.get("merchant_id")
                if merchant_id == merchant.id:
                    request.merchant = merchant
                    return view_func(request, *args, **kwargs)
                else:
                    return redirect("merchant_account:login")
            except Merchant.DoesNotExist:
                raise Http404(f"找不到子域名為 '{shop_param}' 的商家")
        elif shop_id_param:
            try:
                merchant = Merchant.objects.get(subdomain=shop_param)
                merchant_id = request.session.get("merchant_id")
                if merchant_id == merchant.id:
                    request.merchant = merchant
                    return view_func(request, *args, **kwargs)
                else:
                    return redirect("merchant_account:login")
            except Merchant.DoesNotExist:
                raise Http404(f"找不到ID為 '{shop_id_param}' 的商家")
        else:
            if request.method == "GET":
                merchant_id = request.session.get("merchant_id")
                if merchant_id:
                    merchant = get_object_or_404(Merchant, id=merchant_id)
                    if merchant.subdomain:
                        return redirect(f"{request.path}?shop={merchant.subdomain}")
                    else:
                        return redirect(f"{request.path}?shop_id={merchant.id}")
                else:
                    raise Http404("找不到此頁面")
            else:
                merchant_id = request.session.get("merchant_id")
                if merchant_id:
                    request.merchant = get_object_or_404(Merchant, id=merchant_id)
                    return view_func(request, *args, **kwargs)
                else:
                    raise Http404("找不到此頁面")

    return wrapper
