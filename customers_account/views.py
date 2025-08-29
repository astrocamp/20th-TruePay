from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import login as django_login, logout as django_logout
from django.contrib.auth.models import User
from truepay.decorators import customer_login_required
from django.core.paginator import Paginator
from .forms import CustomerRegistrationForm, CustomerLoginForm
from .models import Customer
from payments.models import Order


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
            customer = form.cleaned_data["customer"]
            customer.update_last_login()

            # 建立或取得對應的 Django User
            user, created = User.objects.get_or_create(
                username=f"customer_{customer.email}",
                defaults={
                    "email": customer.email,
                    "first_name": customer.name,
                    "is_active": customer.account_status == "active",
                },
            )

            # 使用 Django 認證系統登入
            django_login(request, user)

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
    # 透過 email 找到對應的 Customer
    try:
        customer = Customer.objects.get(email=request.user.email)
    except Customer.DoesNotExist:
        messages.error(request, "客戶資料不存在")
        return redirect("pages:home")

    # 根據 customer 查詢購買記錄（使用統一的 Order 模型）
    orders = (
        Order.objects.select_related("product__merchant")
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
    # 透過 email 找到對應的 Customer
    try:
        customer = Customer.objects.get(email=request.user.email)
    except Customer.DoesNotExist:
        messages.error(request, "客戶資料不存在")
        return redirect("pages:home")

    # 取得該客戶的訂單記錄統計
    orders = Order.objects.select_related("product__merchant").filter(customer=customer)

    # 統計資料
    total_orders = orders.count()
    total_amount = sum(order.amount for order in orders)
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
