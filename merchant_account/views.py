from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.core.paginator import Paginator
from django.contrib.auth.models import User
from django.contrib.auth import login as django_login
from django.contrib.auth import logout as django_logout
from django.core.paginator import Paginator
from django.db.models import Sum


from truepay.decorators import no_cache_required, shop_required
from .forms import RegisterForm, LoginForm, domain_settings_form
from .models import Merchant
from merchant_marketplace.models import Product
from payments.models import Order


def register(req):
    if req.method == "POST":
        form = RegisterForm(req.POST)

        if form.is_valid():
            subdomain = form.cleaned_data["subdomain"]
            if Merchant.objects.filter(subdomain=subdomain).exists():
                form.add_error(
                    "subdomain", "此網址已被其他商家註冊了，請重新設定其他網址"
                )
                messages.error(req, "註冊失敗，請重新再試")
            else:
                merchant = form.save()
                user, created = User.objects.get_or_create(
                    username=f"merchant_{merchant.Email}",
                    defaults={"email": merchant.Email, "first_name": merchant.Name},
                )
                messages.success(req, "註冊成功！")
                return redirect("merchant_account:login")
        else:
            messages.error(req, "註冊失敗，請重新再試")
    else:
        form = RegisterForm()

    return render(req, "merchant_account/Register.html", {"form": form})


def login(req):
    if req.method == "POST":
        form = LoginForm(req.POST)

        if form.is_valid():
            email = form.cleaned_data["email"]
            password = form.cleaned_data["password"]

            try:
                merchant = Merchant.objects.get(Email=email)

                if merchant.check_password(password):
                    user, created = User.objects.get_or_create(
                        username=f"merchant_{merchant.Email}",
                        defaults={"email": merchant.Email, "first_name": merchant.Name},
                    )
                    django_login(req, user)

                    messages.success(req, "歡迎進入！！！")
                    return redirect("merchant_marketplace:index")
                else:
                    messages.error(req, "密碼錯誤")
            except Merchant.DoesNotExist:
                messages.error(req, "帳號未註冊")
    else:
        form = LoginForm()

    return render(req, "merchant_account/login.html", {"form": form})


def logout(req):
    django_logout(req)
    # 清除所有 session 資料
    req.session.flush()  # 完全清除 session 並重新生成 session key

    # 清除 messages（避免累積）
    storage = messages.get_messages(req)
    for message in storage:
        pass

    messages.success(req, "已成功登出")

    # 建立重導向回應並設定防快取 headers
    response = redirect("merchant_account:login")
    response["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response["Pragma"] = "no-cache"
    response["Expires"] = "0"

    return response


@no_cache_required
@shop_required
def dashboard(request):
    """廠商Dashboard概覽頁面"""
    merchant = request.merchant

    # 獲取商家的基本統計數據
    products = Product.objects.filter(merchant=merchant, is_active=True)
    total_products = products.count()
    recent_products = products.order_by("-created_at")[:5]

    # 獲取交易記錄統計
    orders = Order.objects.filter(product__merchant=merchant)
    total_orders = orders.count()
    recent_orders = orders.select_related("product", "customer").order_by(
        "-created_at"
    )[:5]

    # 計算總收入
    total_revenue = orders.aggregate(total=Sum("amount"))["total"] or 0

    context = {
        "merchant": merchant,
        "total_products": total_products,
        "total_orders": total_orders,
        "total_revenue": total_revenue,
        "recent_products": recent_products,
        "recent_orders": recent_orders,
    }

    return render(request, "merchant_account/dashboard.html", context)


@no_cache_required
@shop_required
def domain_settings(request):
    if request.method == "POST":
        form = domain_settings_form(request.POST, instance=request.merchant)
        if form.is_valid():
            form.save()
            messages.success(request, "網域名稱已更新")
            return redirect("merchant_account:domain_settings")
        else:
            messages.error(request, "設定失敗，請檢查內容")
    else:
        form = domain_settings_form(instance=request.merchant)
    return render(request, "merchant_account/domain_settings.html", {"form": form})


@no_cache_required
@shop_required
def transaction_history(request):
    """廠商交易記錄頁面"""
    # 查詢該商家的所有交易記錄（使用統一的 Order 模型）
    orders = (
        Order.objects.select_related("customer", "product")
        .filter(product__merchant=request.merchant)
        .order_by("-created_at")
    )

    order_items = orders

    # 分頁處理
    paginator = Paginator(order_items, 10)  # 每頁顯示10筆記錄
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    context = {
        "merchant": request.merchant,
        "page_obj": page_obj,
        "order_items": page_obj,
        "role": "merchant",  # 指定角色給模板使用
    }

    return render(request, "merchant_account/transaction_history.html", context)


@no_cache_required
@shop_required
def payment_settings(request):
    """商家金流設定頁面"""
    merchant = request.merchant
    
    if request.method == "POST":
        # 處理表單提交
        try:
            # 收集表單資料
            payment_keys = {}
            
            # 藍新金流設定
            newebpay_merchant_id = request.POST.get('newebpay_merchant_id', '').strip()
            newebpay_hash_key = request.POST.get('newebpay_hash_key', '').strip()
            newebpay_hash_iv = request.POST.get('newebpay_hash_iv', '').strip()
            
            # LINE Pay 設定
            linepay_channel_id = request.POST.get('linepay_channel_id', '').strip()
            linepay_channel_secret = request.POST.get('linepay_channel_secret', '').strip()
            
            # 驗證資料完整性
            if newebpay_merchant_id or newebpay_hash_key or newebpay_hash_iv:
                if not all([newebpay_merchant_id, newebpay_hash_key, newebpay_hash_iv]):
                    messages.error(request, "請完整填寫藍新金流的所有欄位")
                    return redirect('merchant_account:payment_settings')
                payment_keys.update({
                    'newebpay_merchant_id': newebpay_merchant_id,
                    'newebpay_hash_key': newebpay_hash_key,
                    'newebpay_hash_iv': newebpay_hash_iv,
                })
            
            if linepay_channel_id or linepay_channel_secret:
                if not all([linepay_channel_id, linepay_channel_secret]):
                    messages.error(request, "請完整填寫 LINE Pay 的所有欄位")
                    return redirect('merchant_account:payment_settings')
                payment_keys.update({
                    'linepay_channel_id': linepay_channel_id,
                    'linepay_channel_secret': linepay_channel_secret,
                })
            
            # 至少要有一組完整設定
            has_newebpay = all([newebpay_merchant_id, newebpay_hash_key, newebpay_hash_iv])
            has_linepay = all([linepay_channel_id, linepay_channel_secret])
            
            if not has_newebpay and not has_linepay:
                messages.error(request, "請至少完成一組金流設定")
                return redirect('merchant_account:payment_settings')
            
            # 設定金鑰並儲存
            merchant.set_payment_keys(**payment_keys)
            merchant.save()
            
            messages.success(request, "金流設定已成功更新！")
            return redirect('merchant_account:payment_settings')
            
        except Exception as e:
            messages.error(request, f"設定更新失敗：{str(e)}")
            return redirect('merchant_account:payment_settings')
    
    # GET 請求：顯示設定頁面
    context = {
        'merchant': merchant,
        'masked_keys': merchant.get_masked_keys(),
    }
    
    return render(request, "merchant_account/payment_settings.html", context)
