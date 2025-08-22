from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from .models import Product
from merchant_account.models import Merchant


def index(request):
    # 優先使用 subdomain/URL參數指定的商家
    if hasattr(request, 'tenant') and request.tenant:
        products = Product.objects.filter(merchant=request.tenant, is_active=True).order_by("-created_at")
    else:
        # 沒有tenant時，檢查session中的登入商家
        merchant_id = request.session.get("merchant_id")
        if merchant_id:
            merchant = get_object_or_404(Merchant, id=merchant_id)
            products = Product.objects.filter(merchant=merchant, is_active=True).order_by("-created_at")
        else:
            # 都沒有就顯示所有商品
            products = Product.objects.filter(is_active=True).order_by("-created_at")

    return render(request, "merchant_marketplace/index.html", {"products": products})


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


def new(request):
    if request.method == "GET":
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


def edit(request, id):
    product = get_object_or_404(Product, id=id)

    merchant_id = request.session.get("merchant_id")
    if not merchant_id or product.merchant.id != merchant_id:
        messages.error(request, "無權限編輯此商品")
        return redirect("merchant_marketplace:index")

    if request.method == "GET":
        return render(request, "merchant_marketplace/edit.html", {"product": product})

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
            return render(
                request, "merchant_marketplace/edit.html", {"product": product}
            )


def payment_page(request, id):
    """公開的商品收款頁面，任何人都可以查看"""
    product = get_object_or_404(Product, id=id, is_active=True)
    return render(request, "merchant_marketplace/payment_page.html", {"product": product})
