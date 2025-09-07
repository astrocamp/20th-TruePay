import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import never_cache
from django.urls import reverse
from django.contrib import messages
from django.utils import timezone
from datetime import timedelta
from django.db import transaction
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


def _check_pending_order_limit(customer, time_window_minutes=10, max_pending_orders=3, is_retry=False):
    """檢查用戶在指定時間窗口內的待付款訂單數量是否超過限制
        customer: 客戶對象
        time_window_minutes: 時間窗口（分鐘），預設 10 分鐘
        max_pending_orders: 最大待付款訂單數量，預設 3 筆
        is_retry: 是否為重新付款模式，預設 False
    """
    # 如果是重新付款模式，不受限制影響
    if is_retry:
        return True, None
    
    # 計算時間的起始時間
    time_threshold = timezone.now() - timedelta(minutes=time_window_minutes)
    
    # 查詢該用戶在時間內的待付款訂單數量
    pending_count = Order.objects.filter(
        customer=customer,
        status="pending",
        created_at__gte=time_threshold
    ).count()
    
    if pending_count >= max_pending_orders:
        # 查詢該用戶所有待付款訂單
        total_pending = Order.objects.filter(
            customer=customer,
            status="pending"
        ).count()
        
        error_info = {
            'pending_count': pending_count,
            'total_pending': total_pending,
            'time_window_minutes': time_window_minutes,
        }
        return False, error_info
    
    return True, None


def _extract_payment_parameters(request, payment_data=None):
    """統一提取付款參數邏輯"""
    # 從 POST 資料提取安全參數
    provider = request.POST.get("provider")
    product_id = request.POST.get("product_id")
    quantity = request.POST.get("quantity", "1")  # 預設數量為 1

    return provider, product_id, quantity


def _create_order_for_payment(customer, provider, product_id, quantity):
    """統一訂單創建邏輯"""
    try:
        quantity = int(quantity)
        if quantity <= 0:
            raise ValueError("購買數量必須大於 0")
    except (ValueError, TypeError):
        raise ValueError("購買數量格式錯誤")

    # 檢查待付款訂單限制（防止惡意重複下單）
    can_create, limit_error_info = _check_pending_order_limit(customer)
    if not can_create:
        raise ValueError(limit_error_info)

    # 取得商品資訊
    if not product_id:
        raise ValueError("缺少商品ID")

    product = get_object_or_404(Product, id=int(product_id), is_active=True)

    # 統一由後端計算總金額（安全處理）
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
        provider, product_id, quantity = _extract_payment_parameters(
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
            customer, provider, product_id, quantity
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
        error = e.args[0] if e.args else str(e)
        
        # 檢查是否為訂單限制錯誤（error 是 dict 格式）
        if isinstance(error, dict) and 'pending_count' in error:
            from urllib.parse import urlencode
            params = urlencode({
                'pending_count': error['pending_count'],
                'total_pending': error['total_pending'],
                'time_window': error['time_window_minutes']
            })
            return redirect(f"{reverse('payments:order_limit_error')}?{params}")
        
        # 其他錯誤的處理
        error_msg = str(error)
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


@csrf_exempt
@customer_login_required
def retry_payment(request, order_id):
    """重新付款現有的待付款訂單"""
    if request.method != "POST":
        messages.error(request, "無效的請求方式")
        return redirect("customers_account:purchase_history")
    
    try:
        with transaction.atomic():
            order = get_object_or_404(
                Order.objects.select_for_update(), 
                id=order_id
            )
            customer = Customer.objects.get(member=request.user)
            
            # 檢查訂單狀態，只能重新付款待付款的訂單
            if order.status != "pending":
                messages.error(request, f"此訂單狀態為「{order.get_status_display()}」，無法重新付款")
                return redirect("customers_account:purchase_history")
            
            # 檢查商品是否仍然有效
            if not order.product.is_active:
                messages.error(request, "商品已下架，無法重新付款")
                return redirect("customers_account:purchase_history")
            
            # 檢查庫存（防止重新付款時庫存不足）
            if order.product.stock < order.quantity:
                messages.error(request, f"庫存不足，目前庫存：{order.product.stock} 件，訂單數量：{order.quantity} 件")
                return redirect("customers_account:purchase_history")
            
            # 記錄重新付款嘗試（更新訂單時間）
            order.save(update_fields=['updated_at'])
        
        # 處理不同的金流（重新生成付款網址）
        if order.provider == "newebpay":
            return process_newebpay(order, request)
        elif order.provider == "linepay":
            return process_linepay(order, request)
        else:
            messages.error(request, f"不支援的付款方式：{order.provider}")
            return redirect("customers_account:purchase_history")
    
    except Customer.DoesNotExist:
        messages.error(request, "客戶資料不存在")
        return redirect("pages:home")
    except Exception as e:
        logger.error(f"重新付款失敗: {e}")
        messages.error(request, "重新付款處理失敗，請稍後再試")
        return redirect("customers_account:purchase_history")


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


def order_limit_error(request):
    """顯示訂單限制錯誤頁面"""
    pending_count = request.GET.get('pending_count')
    total_pending = request.GET.get('total_pending')
    time_window = request.GET.get('time_window', '10')
    
    context = {
        'pending_count': pending_count,
        'total_pending': total_pending,
        'time_window': time_window,
    }
    
    return render(request, "payments/order_limit_error.html", context)
