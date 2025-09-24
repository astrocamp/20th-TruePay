from django.utils import timezone
from datetime import timedelta
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.http import JsonResponse
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
    products = Product.objects.filter(
        merchant=request.merchant, is_deleted=False
    )  # 預設排除已刪除
    if status == "active":
        products = products.filter(is_active=True)
    elif status == "inactive":
        products = products.filter(is_active=False)
    elif status == "deleted":
        products = Product.objects.filter(merchant=request.merchant, is_deleted=True)
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
            return redirect(
                "merchant_marketplace:detail", request.merchant.subdomain, product.id
            )

        elif action == "deactivate":
            product.is_active = False
            product.save()
            messages.success(request, "商品未上架")
            return redirect(
                "merchant_marketplace:detail", request.merchant.subdomain, product.id
            )

        elif action == "delete":
            # 檢查是否有已售出的票券
            has_tickets = OrderItem.objects.filter(product=product).exists()
            if has_tickets:
                messages.error(request, "此商品已有售出票券，無法刪除")
            else:
                product.is_deleted = True
                product.is_active = False  # 刪除的商品也要下架
                product.save()
                messages.success(request, "商品已刪除")
                return redirect(
                    "merchant_marketplace:index", request.merchant.subdomain
                )

    # 生成嵌入代碼（使用與 embed_system 相同的邏輯）
    ENV = os.getenv("ENV", "development")
    if ENV == "production":
        base_url = "https://truepay.tw"
    else:
        base_url = (
            f"https://{os.getenv('NGROK_URL')}"
            if os.getenv("NGROK_URL")
            else "http://localhost:8000"
        )

    # iframe 嵌入代碼（與 embed_system/views.py:357 相同格式）
    iframe_code = f'<iframe src="{base_url}/embed/product/{product.id}/" width="400" height="600" frameborder="0" style="border: 1px solid #ddd; border-radius: 8px;"></iframe>'

    # JavaScript 嵌入代碼（與 embed_system/views.py:359-360 相同格式）
    script_code = f"""<div class="truepay-widget" data-id="{product.id}"></div>
<script src="{base_url}/embed/embed.js"></script>"""

    context = {
        "product": product,
        "base_domain": os.getenv("NGROK_URL", settings.BASE_DOMAIN),
        "iframe_code": iframe_code,
        "script_code": script_code,
    }
    return render(request, "merchant_marketplace/detail.html", context)


@no_cache_required
@merchant_verified_required
def new(request, subdomain):
    # 設定最小時間為當前時間的下一分鐘
    now = timezone.now()
    min_datetime = now.replace(second=0, microsecond=0) + timedelta(minutes=1)

    if request.method == "POST":
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                product = form.save(commit=False)
                product.merchant = request.merchant
                product.is_active = False  # 預設為下架
                product.save()

                messages.success(request, "商品新增成功！")
                return redirect(
                    "merchant_marketplace:index", request.merchant.subdomain
                )

            except Exception as e:
                messages.error(request, f"新增失敗：{str(e)}")
        else:
            # 表單驗證失敗時顯示錯誤
            for field, errors in form.errors.items():
                for error in errors:
                    field_label = (
                        form.fields[field].label if field in form.fields else field
                    )
                    messages.error(request, f"{field_label}: {error}")
    else:
        form = ProductForm()

    context = {
        "form": form,
        "merchant_phone": request.merchant.Cellphone,
        "current_datetime": min_datetime.strftime("%Y-%m-%dT%H:%M"),
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

    # 設定最小時間為當前時間的下一分鐘
    now = timezone.now()
    min_datetime = now.replace(second=0, microsecond=0) + timedelta(minutes=1)

    if request.method == "POST":
        # 如果已有票券，完全禁止修改
        if has_tickets:
            messages.error(
                request,
                "此商品已有售出票券，為確保票券真實性和消費者權益，所有商品資訊已鎖定無法修改",
            )
        else:
            form = ProductEditForm(request.POST, request.FILES, instance=product)
            if form.is_valid():
                try:
                    form.save()
                    messages.success(request, "商品更新成功！")
                    return redirect(
                        "merchant_marketplace:index", request.merchant.subdomain
                    )
                except Exception as e:
                    messages.error(request, f"更新失敗：{str(e)}")
            else:
                # 表單驗證失敗時顯示錯誤
                for field, errors in form.errors.items():
                    for error in errors:
                        field_label = (
                            form.fields[field].label if field in form.fields else field
                        )
                        messages.error(request, f"{field_label}: {error}")
    else:
        form = ProductEditForm(instance=product)

    context = {
        "form": form,
        "product": product,
        "merchant_phone": product.merchant.Cellphone,
        "has_tickets": has_tickets,
        "current_datetime": min_datetime.strftime("%Y-%m-%dT%H:%M"),
    }
    return render(request, "merchant_marketplace/edit.html", context)


@no_cache_required
@merchant_verified_required
def toggle_status(request, subdomain, id):
    if request.method != "POST":
        return JsonResponse({"success": False, "message": "只允許 POST 請求"}, status=405)

    try:
        product = get_object_or_404(Product, id=id, merchant=request.merchant)

        # 切換上下架狀態
        product.is_active = not product.is_active
        product.save()

        status_text = "上架" if product.is_active else "下架"
        message = f"商品已成功{status_text}"

        return JsonResponse({
            "success": True,
            "is_active": product.is_active,
            "message": message
        })

    except Product.DoesNotExist:
        return JsonResponse({"success": False, "message": "商品不存在"}, status=404)
    except Exception as e:
        return JsonResponse({"success": False, "message": f"操作失敗: {str(e)}"}, status=500)
