import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import never_cache
from django.urls import reverse
from django.contrib import messages
from functools import wraps

from .models import Order
from customers_account.models import Customer
from merchant_marketplace.models import Product
from .newebpay import process_newebpay
from .linepay import process_linepay


# 增強版的 login_required decorator：加入防快取功能
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


logger = logging.getLogger(__name__)


def _extract_payment_parameters(request, payment_data=None):
    """統一提取付款參數邏輯"""
    # 從 POST 資料提取
    provider = request.POST.get("provider")
    product_id = request.POST.get("product_id")
    amt = request.POST.get("amt")
    item_desc = request.POST.get("item_desc")
    quantity = request.POST.get("quantity", "1")  # 預設數量為 1

    return provider, product_id, amt, item_desc, quantity


def _create_order_for_payment(customer, provider, product_id, amount, item_desc, quantity):
    """統一訂單創建邏輯"""
    try:
        quantity = int(quantity)
        if quantity <= 0:
            raise ValueError("購買數量必須大於 0")
    except (ValueError, TypeError):
        raise ValueError("購買數量格式錯誤")

    # 取得商品資訊
    if not product_id:
        raise ValueError("缺少商品ID")

    product = get_object_or_404(Product, id=int(product_id), is_active=True)

    # 根據不同的金流處理金額
    if provider == "newebpay":
        # 藍新金流：驗證前端計算的金額是否正確
        expected_amount = product.price * quantity
        if int(amount) != expected_amount:
            raise ValueError("金額不符")

    elif provider == "linepay":
        # LINE Pay：後端計算總金額
        amount = product.price * quantity

    # 庫存檢查
    if product.stock < quantity:
        raise ValueError(f"庫存不足，目前庫存：{product.stock} 件，購買數量：{quantity} 件")

    # 建立訂單記錄
    order = Order.objects.create(
        provider=provider,
        amount=amount,
        item_description=product.name[:50],
        product=product,
        customer=customer,
        quantity=quantity,
        unit_price=product.price,
        status="pending",
    )

    return order


@csrf_exempt
@login_required(login_url="/customers/login/")
def create_payment(request):
    """統一付款入口 - 支援藍新金流和 LINE Pay"""

    try:
        if request.user.member_type == "merchant":
            messages.info(request, "請使用客戶帳號登入以完成付款")
            return redirect("/customers/login/")
        # 提取付款參數
        provider, product_id, amt, item_desc, quantity = _extract_payment_parameters(
            request, None
        )

        # 驗證參數
        if not provider:
            error_msg = "缺少付款方式參數"
            if request.method == "POST":
                return JsonResponse({"error": error_msg}, status=400)
            messages.error(request, error_msg)
            return redirect("pages:home")

        if provider not in ["newebpay", "linepay"]:
            error_msg = f"無效的付款方式: {provider}"
            if request.method == "POST":
                return JsonResponse({"error": error_msg}, status=400)
            messages.error(request, error_msg)
            return redirect("pages:home")

        # 透過 user 找到對應的 Customer
        customer = Customer.objects.get(member=request.user)

        # 創建訂單
        order = _create_order_for_payment(
            customer, provider, product_id, amt, item_desc, quantity
        )

        # 處理不同的金流
        if provider == "newebpay":
            return process_newebpay(order, request)
        elif provider == "linepay":
            return process_linepay(order, request)

    except Customer.DoesNotExist:
        error_msg = "客戶資料不存在"
        if request.method == "POST":
            return JsonResponse({"error": error_msg}, status=400)
        messages.error(request, error_msg)
        return redirect("pages:home")
    except ValueError as e:
        error_msg = str(e)
        if request.method == "POST":
            return JsonResponse({"error": error_msg}, status=400)
        messages.error(request, error_msg)
        return redirect("pages:home")
    except Exception as e:
        logger.error(f"創建付款失敗: {e}")
        error_msg = "付款處理失敗"
        if request.method == "POST":
            return JsonResponse({"error": error_msg}, status=500)
        messages.error(request, error_msg)
        return redirect("pages:home")


@customer_login_required
def payment_status(request, order_id):
    """查詢訂單狀態"""
    order = get_object_or_404(Order, id=order_id)

    # 透過 user 找到對應的 Customer
    try:
        customer = Customer.objects.get(member=request.user)
    except Customer.DoesNotExist:
        messages.error(request, "客戶資料不存在")
        return redirect("pages:home")

    # 確保用戶只能查看自己的訂單記錄
    if order.customer_id != customer.id:
        messages.error(request, "您沒有權限查看此訂單記錄")
        return redirect("pages:home")

    # 取得訂單相關的票券
    tickets = order.items.all() if order.status == 'paid' else []
    
    context = {
        "payment": order,  # 保持template中的變數名稱
        "tickets": tickets,
    }
    return render(request, "payments/payment_status.html", context)
