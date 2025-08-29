from django.shortcuts import render, get_object_or_404, redirect
from django.http import Http404
from django.contrib import messages
from django.views.decorators.cache import never_cache
from functools import wraps

from truepay.decorators import shop_required
from .models import Product
from merchant_account.models import Merchant
from truepay.decorators import no_cache_required


@no_cache_required
@shop_required
def index(request):
    products = Product.objects.filter(
        merchant=request.merchant, is_active=True
    ).order_by("-created_at")
    return render(request, "merchant_marketplace/index.html", {"products": products})


@no_cache_required
@shop_required
def detail(request, id):
    product = get_object_or_404(Product, id=id, is_active=True)
    if request.method == "POST" and request.POST.get("action") == "delete":
        if product.merchant_id != request.merchant.id:
            messages.error(request, "無權限刪除此商品")
            return redirect("merchant_marketplace:index")

        product.is_active = False
        product.save()
        messages.success(request, "商品已刪除")
        return redirect("/marketplace/")

    return render(request, "merchant_marketplace/detail.html", {"product": product})


@no_cache_required
@shop_required
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
            product = Product.objects.create(
                name=request.POST.get("name"),
                description=request.POST.get("description"),
                price=request.POST.get("price"),
                image=request.FILES.get("image"),
                phone_number=request.POST.get("phone_number"),
                merchant=request.merchant,
            )

            messages.success(request, "商品新增成功！")
            return redirect("/marketplace/")

        except Exception as e:
            messages.error(request, f"新增失敗：{str(e)}")
            return render(request, "merchant_marketplace/new.html")


@no_cache_required
@shop_required
def edit(request, id):
    product = get_object_or_404(Product, id=id)
    if product.merchant_id != request.merchant.id:
        messages.error(request, "無權限編輯此商品")
        return redirect("merchant_marketplace:index")

    if request.method == "GET":
        context = {"product": product, "merchant_phone": product.merchant.Cellphone}
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
            return redirect("/marketplace/")

        except Exception as e:
            messages.error(request, f"更新失敗：{str(e)}")
            context = {"product": product, "merchant_phone": product.merchant.Cellphone}
            return render(request, "merchant_marketplace/edit.html", context)


def payment_page(request, id):
    """公開的商品收款頁面，任何人都可以查看"""
    product = get_object_or_404(Product, id=id, is_active=True)
    return render(
        request, "merchant_marketplace/payment_page.html", {"product": product}
    )
