from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import login as django_login, logout as django_logout
from django.db.models import Sum
from django.db import transaction
from truepay.decorators import customer_login_required
from django.core.paginator import Paginator
from django.utils import timezone
from django.db.models import Q, Count
from .forms import CustomerRegistrationForm, CustomerLoginForm, CustomerProfileUpdateForm, PasswordChangeForm
from django.contrib.auth import update_session_auth_hash
from .models import Customer
from payments.models import Order, OrderItem
from merchant_account.models import Merchant


def register(request):
    if request.method == "POST":
        form = CustomerRegistrationForm(request.POST)
        if form.is_valid():
            try:
                customer = form.save()
                messages.success(request, "註冊成功！請登入您的帳號。")
                return redirect("customers_account:login")
            except Exception as e:
                messages.error(request, "註冊失敗，請重試。")
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{form.fields[field].label}: {error}")
    else:
        form = CustomerRegistrationForm()

    return render(request, "customers/register.html", {"form": form})


def login(request):
    if request.method == "POST":
        form = CustomerLoginForm(request.POST)
        if form.is_valid():
            member = form.cleaned_data["member"]
            customer = form.cleaned_data["customer"]

            # 使用 Django 認證系統登入
            django_login(request, member, backend='django.contrib.auth.backends.ModelBackend')
         
            # 檢查是否有 next 參數（登入後要重導向的頁面）
            next_url = request.GET.get("next") or request.POST.get("next")
            if next_url:
                messages.success(request, "登入成功")
                return redirect(next_url)
            else:
                messages.success(request, "登入成功")
                return redirect("customers_account:dashboard")  # 跳轉到消費者儀表板
        else:
            for error in form.non_field_errors():
                messages.error(request, error)
    else:
        form = CustomerLoginForm()

    return render(request, "customers/login.html", {"form": form})


def logout(request):
    # 使用 Django 登出（這會清除 session 中的認證資訊）
    django_logout(request)

    # 完全清除 session 並重新生成 session key
    request.session.flush()

    messages.success(request, "已成功登出")

    # 建立重導向回應並設定防快取 headers
    response = redirect("pages:home")
    response["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response["Pragma"] = "no-cache"
    response["Expires"] = "0"

    return response


@customer_login_required
def purchase_history(request):
    """消費者購買記錄頁面"""
    # 透過 user 找到對應的 Customer
    try:
        customer = Customer.objects.get(member=request.user)
    except Customer.DoesNotExist:
        messages.error(request, "客戶資料不存在")
        return redirect("pages:home")

    # 根據 customer 查詢購買記錄（使用統一的 Order 模型）
    orders = (
        Order.objects.select_related("product__merchant")
        .prefetch_related("items")  # 預載入票券資料
        .filter(customer=customer)
        .order_by("-created_at")
    )

    # 為了向後兼容，我們仍然使用 order_items 這個變數名
    order_items = orders

    # 分頁處理
    paginator = Paginator(order_items, 10)  # 每頁顯示10筆記錄
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    context = {
        "customer": customer,
        "page_obj": page_obj,
        "order_items": page_obj,
        "role": "customer",  # 指定角色給模板使用
    }

    return render(request, "customers/purchase_history.html", context)


@customer_login_required
def dashboard(request):
    """消費者儀表板頁面"""
    # 透過 user 找到對應的 Customer
    try:
        customer = Customer.objects.get(member=request.user)
    except Customer.DoesNotExist:
        messages.error(request, "客戶資料不存在")
        return redirect("pages:home")

    # 取得該客戶的訂單記錄統計
    orders = Order.objects.select_related("product__merchant").filter(customer=customer)

    # 統計資料
    total_orders = orders.count()
    # 只計算已付款訂單的金額（使用 aggregate 更高效）
    total_amount = orders.filter(status="paid").aggregate(total=Sum("amount"))["total"] or 0
    pending_orders = orders.filter(status="pending").count()

    # 最近5筆購買記錄
    recent_orders = orders.order_by("-created_at")[:5]

    context = {
        "customer": customer,
        "total_orders": total_orders,
        "total_amount": total_amount,
        "pending_orders": pending_orders,
        "recent_orders": recent_orders,
    }

    return render(request, "customers/dashboard.html", context)


@customer_login_required
def ticket_wallet(request):
    """消費者票券錢包頁面"""
    # 透過 member 找到對應的 Customer
    try:
        customer = Customer.objects.get(member=request.user)
    except Customer.DoesNotExist:
        messages.error(request, "客戶資料不存在")
        return redirect("pages:home")
    
    # 取得篩選參數
    status_filter = request.GET.get('status', '')
    merchant_filter = request.GET.get('merchant', '')
    order_filter = request.GET.get('order', '')
    
    # 先將已過期且未標記的票券狀態更新為 expired（避免每次模板內判斷）
    now = timezone.now()
    OrderItem.objects.filter(customer=customer, status='unused', valid_until__lt=now).update(status='expired')

    # 基本查詢：取得該客戶的所有票券
    tickets = OrderItem.objects.select_related(
        'product__merchant', 'order'
    ).filter(customer=customer).order_by('-created_at')
    
    # 狀態篩選
    if status_filter:
        tickets = tickets.filter(status=status_filter)
    
    # 商家篩選
    if merchant_filter:
        try:
            merchant_id = int(merchant_filter)
            tickets = tickets.filter(product__merchant_id=merchant_id)
        except (ValueError, TypeError):
            pass
    
    # 訂單編號篩選（支援訂單ID或訂單編號）
    if order_filter:
        # 先嘗試用訂單ID篩選
        try:
            order_id = int(order_filter)
            tickets = tickets.filter(order_id=order_id)
        except (ValueError, TypeError):
            # 如果不是數字，則用訂單編號篩選
            tickets = tickets.filter(order__provider_order_id=order_filter)
    
    # 取得統計資料
    all_tickets = OrderItem.objects.filter(customer=customer)
    ticket_stats = all_tickets.aggregate(
        total=Count('id'),
        unused=Count('id', filter=Q(status='unused')),
        used=Count('id', filter=Q(status='used')),
        expired=Count('id', filter=Q(status='expired'))
    )
    
    # 取得所有相關商家（用於篩選下拉選單）
    merchants = Merchant.objects.filter(
        product__orderitem__customer=customer
    ).distinct().order_by('ShopName')
    
    # 分頁處理
    paginator = Paginator(tickets, 10)  # 每頁顯示10筆記錄
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'customer': customer,
        'tickets': page_obj,
        'page_obj': page_obj,
        'is_paginated': page_obj.has_other_pages(),
        'ticket_stats': ticket_stats,
        'merchants': merchants,
        'now': now,
    }
    
    return render(request, "customers/ticket_wallet.html", context)


@customer_login_required
def profile_settings(request):
    """消費者會員資料修改頁面"""
    # 透過 user 找到對應的 Customer
    try:
        customer = Customer.objects.get(member=request.user)
    except Customer.DoesNotExist:
        messages.error(request, "客戶資料不存在")
        return redirect("pages:home")

    if request.method == "POST":
        form_type = request.POST.get("form_type")
        
        if form_type == "profile":
            # 處理個人資料修改
            form = CustomerProfileUpdateForm(request.POST, instance=customer, user=request.user)
            if form.is_valid():
                form.save()
                messages.success(request, "個人資料已成功更新")
                return redirect("customers_account:profile_settings")
            else:
                for field, errors in form.errors.items():
                    for error in errors:
                        messages.error(request, f"{form.fields[field].label if field in form.fields else field}: {error}")
        
        elif form_type == "password":
            # 處理密碼修改
            password_form = PasswordChangeForm(request.user, request.POST)
            if password_form.is_valid():
                password_form.save()
                # 更新 session，避免用戶被登出
                update_session_auth_hash(request, request.user)
                messages.success(request, "密碼已成功修改")
                return redirect("customers_account:profile_settings")
            else:
                for field, errors in password_form.errors.items():
                    for error in errors:
                        messages.error(request, f"{password_form.fields[field].label if field in password_form.fields else field}: {error}")
    
    # GET 請求或表單驗證失敗時顯示表單
    profile_form = CustomerProfileUpdateForm(instance=customer, user=request.user)
    password_form = PasswordChangeForm(request.user)
    
    
    context = {
        "customer": customer,
        "profile_form": profile_form,
        "password_form": password_form,
    }
    
    return render(request, "customers/profile_settings.html", context)


@customer_login_required
def cancel_order(request, order_id):
    """取消待付款訂單"""
    if request.method != "POST":
        messages.error(request, "無效的請求方式")
        return redirect("customers_account:purchase_history")
    
    try:
        # 透過 user 找到對應的 Customer
        customer = Customer.objects.get(member=request.user)
        
        with transaction.atomic():
            # 取得訂單並檢查權限
            order = Order.objects.select_for_update().get(
                id=order_id, 
                customer=customer
            )
            
            # 檢查訂單狀態，只能取消待付款的訂單
            if order.status != "pending":
                messages.error(request, f"此訂單狀態為「{order.get_status_display()}」，無法取消")
                return redirect("customers_account:purchase_history")
            
            # 更新訂單狀態為已取消
            order.status = "cancelled"
            order.save(update_fields=['status', 'updated_at'])
            
        messages.success(request, f"訂單 {order.provider_order_id} 已成功取消")
        return redirect("customers_account:purchase_history")
        
    except Customer.DoesNotExist:
        messages.error(request, "客戶資料不存在")
        return redirect("pages:home")
    except Order.DoesNotExist:
        messages.error(request, "訂單不存在或您沒有權限操作")
        return redirect("customers_account:purchase_history")
    except Exception as e:
        messages.error(request, "取消訂單失敗，請稍後再試")
        return redirect("customers_account:purchase_history")
