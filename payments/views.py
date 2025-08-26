import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from django.contrib import messages

from .models import Order
from customers_account.models import Customer
from merchant_marketplace.models import Product
from .newebpay import process_newebpay
from .linepay import process_linepay


logger = logging.getLogger(__name__)


def _extract_payment_parameters(request, payment_data=None):
    """統一提取付款參數邏輯"""
    if payment_data:
        # 從 session 中的暫存資料提取
        provider = payment_data.get('provider')
        product_id = payment_data.get('product_id')
        amt = payment_data.get('amt')
        item_desc = payment_data.get('item_desc')
    else:
        # 從 POST 資料提取
        provider = request.POST.get('provider')
        product_id = request.POST.get('product_id')
        amt = request.POST.get('amt')
        item_desc = request.POST.get('item_desc')
    
    
    return provider, product_id, amt, item_desc


def _create_order_for_payment(customer, provider, product_id, amount, item_desc):
    """統一訂單創建邏輯"""
    # 根據不同的金流處理參數
    if provider == 'newebpay':
        # 藍新金流：從 item_desc 解析 product_id
        if '|ProductID:' in item_desc:
            product_id = item_desc.split('|ProductID:')[1]
        else:
            raise ValueError("商品資訊錯誤")
        amount = int(float(amount))
        
    elif provider == 'linepay':
        # LINE Pay：直接使用 product_id
        if not product_id:
            raise ValueError("缺少商品ID")
        product = get_object_or_404(Product, id=product_id, is_active=True)
        amount = product.price
    
    # 取得商品資訊
    product = get_object_or_404(Product, id=int(product_id), is_active=True)
    
    # 建立訂單記錄
    order = Order.objects.create(
        provider=provider,
        amount=amount,
        item_description=f"{product.name}|ProductID:{product.id}",
        product=product,
        customer=customer,
        quantity=1,
        unit_price=product.price,
        status='pending'
    )
    
    return order


@csrf_exempt
def create_payment(request):
    """統一付款入口 - 支援藍新金流和 LINE Pay"""
    # 檢查登入狀態
    if not request.user.is_authenticated:
        if request.method == "POST":
            # 暫存付款資料到 session
            request.session['payment_data'] = {
                'provider': request.POST.get('provider'),
                'product_id': request.POST.get('product_id'),
                'amt': request.POST.get('amt'),
                'item_desc': request.POST.get('item_desc')
            }
        login_url = reverse('customers_account:login')
        next_url = request.get_full_path()
        return redirect(f"{login_url}?next={next_url}")
    
    # 取得付款參數
    payment_data = None
    if request.method == "GET":
        payment_data = request.session.get('payment_data')
        if not payment_data:
            return redirect("pages:home")
    
    try:
        # 提取付款參數
        provider, product_id, amt, item_desc = _extract_payment_parameters(request, payment_data)
        
        # 驗證參數
        if not provider:
            error_msg = "缺少付款方式參數"
            if request.method == "POST":
                return JsonResponse({"error": error_msg}, status=400)
            messages.error(request, error_msg)
            return redirect("pages:home")
        
        if provider not in ['newebpay', 'linepay']:
            error_msg = f"無效的付款方式: {provider}"
            if request.method == "POST":
                return JsonResponse({"error": error_msg}, status=400)
            messages.error(request, error_msg)
            return redirect("pages:home")
        
        # 透過 email 找到對應的 Customer
        customer = Customer.objects.get(email=request.user.email)
        
        # 創建訂單
        order = _create_order_for_payment(customer, provider, product_id, amt, item_desc)
        
        # 清除暫存的付款資料
        if 'payment_data' in request.session:
            del request.session['payment_data']
        
        # 處理不同的金流
        if provider == 'newebpay':
            return process_newebpay(order, request)
        elif provider == 'linepay':
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




@login_required(login_url='/customers/login/')
def payment_status(request, order_id):
    """查詢訂單狀態"""
    order = get_object_or_404(Order, id=order_id)
    
    # 透過 email 找到對應的 Customer
    try:
        customer = Customer.objects.get(email=request.user.email)
    except Customer.DoesNotExist:
        messages.error(request, "客戶資料不存在")
        return redirect('pages:home')
    
    # 確保用戶只能查看自己的訂單記錄
    if order.customer_id != customer.id:
        messages.error(request, "您沒有權限查看此訂單記錄")
        return redirect('pages:home')
    
    context = {
        "order": order,
    }
    return render(request, "payments/payment_status.html", context)