from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages

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
        return redirect("merchant_marketplace:index")

    return render(request, "merchant_marketplace/detail.html", {"product": product})


@no_cache_required
@shop_required
def new(request):
    if request.method == "GET":
        context = {"merchant_phone": request.merchant.Cellphone}
        return render(request, "merchant_marketplace/new.html", context)

    elif request.method == "POST":
        try:
            stock = int(request.POST.get("stock", 1))
            if stock < 1:
                raise ValueError("庫存數量必須至少為 1 件")
                
            product = Product.objects.create(
                name=request.POST.get("name"),
                description=request.POST.get("description"),
                price=request.POST.get("price"),
                stock=stock,
                image=request.FILES.get("image"),
                phone_number=request.POST.get("phone_number"),
                merchant=request.merchant,
            )

            messages.success(request, "商品新增成功！")
            return redirect("merchant_marketplace:index")

        except Exception as e:
            messages.error(request, f"新增失敗：{str(e)}")
            context = {"merchant_phone": request.merchant.Cellphone}
            return render(request, "merchant_marketplace/new.html", context)
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
            
            # 更新庫存，允許設為 0（賣完狀態）
            stock = int(request.POST.get("stock", product.stock))
            if stock < 0:
                raise ValueError("庫存數量不能為負數")
            product.stock = stock

            # 只有在有新圖片時才更新
            if request.FILES.get("image"):
                product.image = request.FILES.get("image")

            product.phone_number = request.POST.get(
                "phone_number", product.phone_number
            )
            product.save()

            messages.success(request, "商品更新成功！")
            return redirect("merchant_marketplace:index")

        except Exception as e:
            messages.error(request, f"更新失敗：{str(e)}")
            context = {"product": product, "merchant_phone": product.merchant.Cellphone}
            return render(request, "merchant_marketplace/edit.html", context)
