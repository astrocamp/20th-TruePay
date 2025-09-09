from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import login as django_login, logout as django_logout
from django.db.models import Sum
from truepay.decorators import customer_login_required
from django.core.paginator import Paginator
from django.utils import timezone
from django.db.models import Q, Count
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import json
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
    now = timezone.now()
    all_tickets = OrderItem.objects.filter(customer=customer)
    ticket_stats = all_tickets.aggregate(
        total=Count('id'),
        unused=Count('id', filter=Q(status='unused')),
        used=Count('id', filter=Q(status='used')),
        expired=Count('id', filter=Q(status='unused', valid_until__lt=now))
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


# TOTP 二階段驗證相關視圖
@customer_login_required
def totp_setup(request):
    """TOTP 設置頁面 - 顯示 QR Code"""
    try:
        customer = Customer.objects.get(member=request.user)
    except Customer.DoesNotExist:
        messages.error(request, "客戶資料不存在")
        return redirect("pages:home")
    
    # 如果已經啟用 TOTP，重導向到設定頁面
    if customer.totp_enabled:
        messages.info(request, "您已經啟用二階段驗證")
        return redirect("customers_account:totp_manage")
    
    # 生成新的 TOTP 密鑰和 QR Code
    customer.generate_totp_secret()
    qr_code = customer.generate_qr_code()
    
    # 檢查是否有next參數
    next_url = request.GET.get('next')
    
    context = {
        'customer': customer,
        'qr_code': qr_code,
        'totp_secret': customer.totp_secret_key,
        'next_url': next_url,
    }
    
    return render(request, 'customers/totp_setup.html', context)


@customer_login_required
def totp_enable(request):
    """啟用 TOTP - 驗證用戶輸入的代碼"""
    try:
        customer = Customer.objects.get(member=request.user)
    except Customer.DoesNotExist:
        messages.error(request, "客戶資料不存在")
        return redirect("pages:home")
    
    if request.method == 'POST':
        totp_code = request.POST.get('totp_code', '').strip()
        
        if not totp_code:
            messages.error(request, "請輸入驗證代碼")
            return redirect("customers_account:totp_setup")
        
        # 臨時驗證 TOTP 代碼
        import pyotp
        if customer.totp_secret_key:
            totp = pyotp.TOTP(customer.totp_secret_key)
            if totp.verify(totp_code, valid_window=1):
                # 驗證成功，啟用 TOTP
                customer.enable_totp()
                backup_tokens = customer.backup_tokens
                
                # 檢查是否有next參數
                next_url = request.GET.get('next') or request.POST.get('next')
                
                messages.success(request, "二階段驗證已成功啟用！請保存您的備用恢復代碼。")
                return render(request, 'customers/totp_backup_codes.html', {
                    'customer': customer,
                    'backup_tokens': backup_tokens,
                    'next_url': next_url
                })
            else:
                messages.error(request, "驗證代碼錯誤，請重新輸入")
        else:
            messages.error(request, "設置錯誤，請重新開始設置")
    
    return redirect("customers_account:totp_setup")


@customer_login_required
def totp_manage(request):
    """TOTP 管理頁面 - 顯示當前狀態和管理選項"""
    try:
        customer = Customer.objects.get(member=request.user)
    except Customer.DoesNotExist:
        messages.error(request, "客戶資料不存在")
        return redirect("pages:home")
    
    context = {
        'customer': customer,
        'backup_tokens': customer.backup_tokens if customer.totp_enabled else [],
    }
    
    return render(request, 'customers/totp_manage.html', context)


@customer_login_required
def totp_disable(request):
    """停用 TOTP"""
    try:
        customer = Customer.objects.get(member=request.user)
    except Customer.DoesNotExist:
        messages.error(request, "客戶資料不存在")
        return redirect("pages:home")
    
    if request.method == 'POST':
        # 要求用戶確認密碼或 TOTP 代碼
        password = request.POST.get('password', '').strip()
        totp_code = request.POST.get('totp_code', '').strip()
        
        # 驗證密碼
        if password and request.user.check_password(password):
            customer.disable_totp()
            messages.success(request, "二階段驗證已停用")
            return redirect("customers_account:profile_settings")
        # 或驗證 TOTP 代碼
        elif totp_code and customer.verify_totp(totp_code):
            customer.disable_totp()
            messages.success(request, "二階段驗證已停用")
            return redirect("customers_account:profile_settings")
        else:
            messages.error(request, "密碼或驗證代碼錯誤")
    
    return redirect("customers_account:totp_manage")


@customer_login_required
def regenerate_backup_tokens(request):
    """重新生成備用恢復代碼"""
    try:
        customer = Customer.objects.get(member=request.user)
    except Customer.DoesNotExist:
        messages.error(request, "客戶資料不存在")
        return redirect("pages:home")
    
    if not customer.totp_enabled:
        messages.error(request, "請先啟用二階段驗證")
        return redirect("customers_account:totp_setup")
    
    if request.method == 'POST':
        # 驗證 TOTP 代碼
        totp_code = request.POST.get('totp_code', '').strip()
        
        if totp_code and customer.verify_totp(totp_code):
            backup_tokens = customer.generate_backup_tokens()
            messages.success(request, "備用恢復代碼已重新生成！請保存新的代碼。")
            return render(request, 'customers/totp_backup_codes.html', {
                'customer': customer,
                'backup_tokens': backup_tokens,
                'is_regenerate': True
            })
        else:
            messages.error(request, "驗證代碼錯誤")
    
    return redirect("customers_account:totp_manage")


# AJAX API 用於交易過程中驗證 TOTP
@csrf_exempt
@require_http_methods(["POST"])
@customer_login_required
def verify_totp_api(request):
    """API 端點用於驗證 TOTP 代碼"""
    try:
        customer = Customer.objects.get(member=request.user)
        data = json.loads(request.body)
        totp_code = data.get('totp_code', '').strip()
        
        if not customer.totp_enabled:
            return JsonResponse({
                'success': False,
                'error': '二階段驗證未啟用'
            })
        
        if not totp_code:
            return JsonResponse({
                'success': False,
                'error': '請輸入驗證代碼'
            })
        
        if customer.verify_totp(totp_code):
            return JsonResponse({
                'success': True,
                'message': '驗證成功'
            })
        else:
            return JsonResponse({
                'success': False,
                'error': '驗證代碼錯誤'
            })
            
    except Customer.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': '客戶資料不存在'
        })
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': '無效的請求格式'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': '系統錯誤'
        })
