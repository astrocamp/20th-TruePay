from django.utils.dateparse import parse_datetime
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.conf import settings
import os
from .models import Product
from .forms import ProductForm, ProductEditForm
from merchant_account.models import Merchant
from truepay.decorators import no_cache_required, merchant_verified_required
from payments.models import OrderItem


@no_cache_required
def index(request, subdomain):
    status = request.GET.get("status")
    products = Product.objects.filter(merchant=request.merchant)
    if status == "active":
        products = products.filter(is_active=True)
    elif status == "inactive":
        products = products.filter(is_active=False)
    products = products.order_by("-created_at")
    return render(request, "merchant_marketplace/index.html", {"products": products})


@no_cache_required
@merchant_verified_required
def detail(request, subdomain, id):
    product = get_object_or_404(Product, id=id, merchant=request.merchant)
    
    if request.method == "POST":
        action = request.POST.get("action")
        
        if action == "activate":
            product.is_active = True
            product.save()
            messages.success(request, "商品已上架")
            return redirect("merchant_marketplace:detail", request.merchant.subdomain, product.id)
            
        elif action == "deactivate":
            product.is_active = False
            product.save()
            messages.success(request, "商品已下架")
            return redirect("merchant_marketplace:detail", request.merchant.subdomain, product.id)
            
        elif action == "delete":
            product.is_active = False
            product.save()
            messages.success(request, "商品已刪除")
            return redirect("merchant_marketplace:index", request.merchant.subdomain)

    context = {
        "product": product,
        "base_domain": os.getenv("NGROK_URL", settings.BASE_DOMAIN)
    }
    return render(request, "merchant_marketplace/detail.html", context)


@no_cache_required
@merchant_verified_required
def new(request, subdomain):
    if request.method == "GET":
        form = ProductForm()
        context = {
            "form": form,
            "merchant_phone": request.merchant.Cellphone
        }
        return render(request, "merchant_marketplace/new.html", context)

    elif request.method == "POST":
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                stock = form.cleaned_data.get("stock", 1)
                if stock < 1:
                    raise ValueError("庫存數量必須至少為 1 件")

                product = form.save(commit=False)
                product.merchant = request.merchant
                product.is_active = False  # 預設為下架
                product.save()

                messages.success(request, "商品新增成功！")
                return redirect("merchant_marketplace:index", request.merchant.subdomain)

            except Exception as e:
                messages.error(request, f"新增失敗：{str(e)}")
        else:
            # 顯示表單驗證錯誤
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{form.fields[field].label if field in form.fields else field}：{error}")

        context = {
            "form": form,
            "merchant_phone": request.merchant.Cellphone
        }
        return render(request, "merchant_marketplace/new.html", context)


@no_cache_required
@merchant_verified_required
def edit(request, subdomain, id):
    product = get_object_or_404(Product, id=id)
    if product.merchant_id != request.merchant.id:
        messages.error(request, "無權限編輯此商品")
        return redirect("merchant_marketplace:index", request.merchant.subdomain)

    # 檢查是否有票券，決定是否可以修改驗證方式（GET/POST 共用）
    has_tickets = OrderItem.objects.filter(product=product).exists()

    if request.method == "GET":
        form = ProductEditForm(instance=product)
        context = {
            "form": form,
            "product": product,
            "merchant_phone": product.merchant.Cellphone,
            "has_tickets": has_tickets
        }
        return render(request, "merchant_marketplace/edit.html", context)

    elif request.method == "POST":
        # 如果已有票券，完全禁止修改
        if has_tickets:
            messages.error(request, "此商品已有售出票券，為確保票券真實性和消費者權益，所有商品資訊已鎖定無法修改")
            context = {
                "form": ProductEditForm(instance=product),
                "product": product,
                "merchant_phone": product.merchant.Cellphone,
                "has_tickets": has_tickets
            }
            return render(request, "merchant_marketplace/edit.html", context)

        form = ProductEditForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            try:
                stock = form.cleaned_data.get("stock", product.stock)
                if stock < 0:
                    raise ValueError("庫存數量不能為負數")

                product = form.save()
                messages.success(request, "商品更新成功！")
                return redirect("merchant_marketplace:index", request.merchant.subdomain)

            except Exception as e:
                messages.error(request, f"更新失敗：{str(e)}")
        else:
            # 顯示表單驗證錯誤
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{form.fields[field].label if field in form.fields else field}：{error}")

        context = {
            "form": form,
            "product": product,
            "merchant_phone": product.merchant.Cellphone,
            "has_tickets": has_tickets
        }
        return render(request, "merchant_marketplace/edit.html", context)
