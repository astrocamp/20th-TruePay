from functools import wraps
from django.shortcuts import get_object_or_404, redirect
from django.http import Http404
from merchant_account.models import Merchant


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

                merchant_id = request.session.get("merchant_id")
                if merchant_id == merchant.id:
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
