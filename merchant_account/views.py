from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse

from .forms import RegisterForm, LoginForm, domain_settings_form
from .models import Merchant
from django.views.decorators.csrf import csrf_exempt
from merchant_marketplace.models import Product
from payments.models import Order
from django.core.paginator import Paginator


# Create your views here.
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
                form.save()
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

                if merchant.Password == password:
                    req.session["merchant_id"] = merchant.id
                    req.session["merchant_name"] = merchant.Name
                    messages.success(req, "歡迎進入！！！")
                    if merchant.subdomain:
                        return redirect(f"/marketplace/?shop={merchant.subdomain}")
                    else:
                        return redirect(f"/marketplace/?shop_id={merchant.id}")
                else:
                    messages.error(req, "密碼錯誤")
            except Merchant.DoesNotExist:
                messages.error(req, "帳號未註冊")
    else:
        form = LoginForm()

    return render(req, "merchant_account/login.html", {"form": form})


def logout(req):
    if "merchant_id" in req.session:
        del req.session["merchant_id"]
    if "merchant_name" in req.session:
        del req.session["merchant_name"]

    storage = messages.get_messages(req)
    for message in storage:
        pass

    messages.success(req, "已成功登出")
    return redirect("merchant_account:login")


def domain_settings(request):
    merchant_id = request.session.get("merchant_id")
    if not merchant_id:
        messages.error(request, "請先登入")
        return redirect("merchant_account:login")
    merchant = get_object_or_404(Merchant, id=merchant_id)
    if request.method == "POST":
        form = domain_settings_form(request.POST, instance=merchant)
        if form.is_valid():
            form.save()
            messages.success(request, "網域名稱已更新")
            return redirect("merchant_account:domain_settings")
        else:
            messages.error(request, "設定失敗，請檢查內容")
    else:
        form = domain_settings_form(instance=merchant)
    return render(request, "merchant_account/domain_settings.html", {"form": form})



def transaction_history(request):
    """廠商交易記錄頁面"""
    # 檢查商家是否已登入
    merchant_id = request.session.get("merchant_id")
    if not merchant_id:
        messages.error(request, "請先登入")
        return redirect("merchant_account:login")
    merchant = get_object_or_404(Merchant, id=merchant_id)

    # 查詢該商家的所有交易記錄（使用統一的 Order 模型）
    orders = (
        Order.objects.select_related("customer", "product")
        .filter(product__merchant=merchant)
        .order_by("-created_at")
    )

    # 為了向後兼容，我們仍然使用 order_items 這個變數名
    order_items = orders

    # 分頁處理
    paginator = Paginator(order_items, 10)  # 每頁顯示10筆記錄
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    context = {
        "merchant": merchant,
        "page_obj": page_obj,
        "order_items": page_obj,
        "role": "merchant",  # 指定角色給模板使用
    }

    return render(request, "merchant_account/transaction_history.html", context)
