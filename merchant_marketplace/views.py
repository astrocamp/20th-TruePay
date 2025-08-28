from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.views.decorators.cache import never_cache
from functools import wraps
from .models import Product
from merchant_account.models import Merchant
from django.http import Http404


# 自定義 decorator：檢查商家登入狀態並防止快取
def merchant_login_required(view_func):
    @wraps(view_func)
    @never_cache
    def _wrapped_view(request, *args, **kwargs):
        merchant_id = request.session.get("merchant_id")
        if not merchant_id:
            messages.error(request, "請先登入")
            return redirect("merchant_account:login")
        
        # 設定防快取 headers
        response = view_func(request, *args, **kwargs)
        if hasattr(response, '__setitem__'):
            response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
            response['Pragma'] = 'no-cache'
            response['Expires'] = '0'
        
        return response
    return _wrapped_view


@merchant_login_required
def index(request):
    shop_param = request.GET.get("shop")
    shop_id_param = request.GET.get("shop_id")
    if shop_param:
        try:
            merchant = Merchant.objects.get(subdomain=shop_param)
            merchant_id = request.session.get("merchant_id")
            if merchant_id == merchant.id:
                products = Product.objects.filter(
                    merchant=merchant, is_active=True
                ).order_by("-created_at")
                return render(
                    request, "merchant_marketplace/index.html", {"products": products}
                )
            else:
                return redirect("merchant_account:login")
        except Merchant.DoesNotExist:
            raise Http404(f"找不到子域名為 '{shop_param}' 的商家")
    elif shop_id_param:
        try:
            merchant = Merchant.objects.get(id=shop_id_param)
            merchant_id = request.session.get("merchant_id")
            if merchant_id == merchant.id:
                products = Product.objects.filter(
                    merchant=merchant, is_active=True
                ).order_by("-created_at")
                return render(
                    request, "merchant_marketplace/index.html", {"products": products}
                )
            else:
                return redirect("merchant_account:login")
        except Merchant.DoesNotExist:
            raise Http404(f"找不到 ID 為 '{shop_id_param}' 的商家")
    # 沒有指定商家參數時，檢查 session 中的登入商家
    merchant_id = request.session.get("merchant_id")
    if merchant_id:
        merchant = get_object_or_404(Merchant, id=merchant_id)
        products = Product.objects.filter(merchant=merchant, is_active=True).order_by(
            "-created_at"
        )
        return render(
            request, "merchant_marketplace/index.html", {"products": products}
        )
    else:
        # 沒有登入且沒有指定商家，返回 404
        raise Http404("找不到此頁面")


@merchant_login_required
def detail(request, id):
    product = get_object_or_404(Product, id=id, is_active=True)
    if request.method == "POST" and request.POST.get("action") == "delete":
        merchant_id = request.session.get("merchant_id")
        if not merchant_id or product.merchant.id != merchant_id:
            messages.error(request, "無權限刪除此商品")
            return redirect("merchant_marketplace:index")

        product.is_active = False
        product.save()
        messages.success(request, "商品已刪除")
        return redirect("merchant_marketplace:index")

    return render(request, "merchant_marketplace/detail.html", {"product": product})


@merchant_login_required
def new(request):
    if request.method == "GET":
        merchant_id = request.session.get("merchant_id")
        if merchant_id:
            merchant = get_object_or_404(Merchant, id=merchant_id)
            context = {"merchant_phone": merchant.Cellphone}
            return render(request, "merchant_marketplace/new.html", context)
        else:
            return render(request, "merchant_marketplace/new.html")

    elif request.method == "POST":
        try:
            merchant_id = request.session.get("merchant_id")
            if not merchant_id:
                messages.error(request, "請先登入")
                return redirect("merchant_account:login")

            merchant = get_object_or_404(Merchant, id=merchant_id)
            product = Product.objects.create(
                name=request.POST.get("name"),
                description=request.POST.get("description"),
                price=request.POST.get("price"),
                image=request.FILES.get("image"),
                phone_number=request.POST.get("phone_number"),
                merchant=merchant,
            )

            messages.success(request, "商品新增成功！")
            return redirect("merchant_marketplace:detail", id=product.id)

        except Exception as e:
            messages.error(request, f"新增失敗：{str(e)}")
            return render(request, "merchant_marketplace/new.html")


@merchant_login_required
def edit(request, id):
    product = get_object_or_404(Product, id=id)
    merchant_id = request.session.get("merchant_id")
    if not merchant_id or product.merchant.id != merchant_id:
        messages.error(request, "無權限編輯此商品")
        return redirect("merchant_marketplace:index")

    if request.method == "GET":
        context = {
            "product": product,
            "merchant_phone": product.merchant.Cellphone
        }
        return render(request, "merchant_marketplace/edit.html", context)

    elif request.method == "POST":
        try:
            product.name = request.POST.get("name", product.name)
            product.description = request.POST.get("description", product.description)
            product.price = request.POST.get("price", product.price)

            # 只有在有新圖片時才更新
            if request.FILES.get("image"):
                product.image = request.FILES.get("image")

            product.phone_number = request.POST.get(
                "phone_number", product.phone_number
            )
            product.save()

            messages.success(request, "商品更新成功！")
            return redirect("merchant_marketplace:detail", id=product.id)

        except Exception as e:
            messages.error(request, f"更新失敗：{str(e)}")
            context = {
                "product": product,
                "merchant_phone": product.merchant.Cellphone
            }
            return render(request, "merchant_marketplace/edit.html", context)


def payment_page(request, id):
    """公開的商品收款頁面，任何人都可以查看"""
    product = get_object_or_404(Product, id=id, is_active=True)
    return render(
        request, "merchant_marketplace/payment_page.html", {"product": product}
    )
