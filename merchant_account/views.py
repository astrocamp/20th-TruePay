from django.shortcuts import render, redirect
from django.contrib import messages
from django.core.paginator import Paginator
from django.contrib.auth.models import User
from django.contrib.auth import login as django_login
from django.contrib.auth import logout as django_logout
from django.contrib.auth import get_user_model
from django.core.paginator import Paginator
from django.db.models import Sum
from django.views.decorators.http import require_POST


from truepay.decorators import no_cache_required
from .forms import RegisterForm, LoginForm, domain_settings_form
from .models import Merchant
from payments.models import Order, OrderItem, TicketValidation
from merchant_marketplace.models import Product
from payments.models import Order


def register(req):
    if req.method == "POST":
        form = RegisterForm(req.POST)

        if form.is_valid():
            try:
                merchant = form.save()
                messages.success(req, "註冊成功！")
                return redirect("merchant_account:login")
            except Exception as e:
                messages.error(req, "註冊失敗，請重新再試")
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(req, f"{form.fields[field].label}: {error}")
    else:
        form = RegisterForm()

    return render(req, "merchant_account/Register.html", {"form": form})


def login(req):
    if req.method == "POST":
        form = LoginForm(req.POST)

        if form.is_valid():
            member = form.cleaned_data["member"]
            merchant = form.cleaned_data["merchant"]

            django_login(req, member)

            messages.success(req, "歡迎進入！！！")
            return redirect("merchant_account:dashboard", merchant.subdomain)
        else:
            for error in form.non_field_errors():
                messages.error(req, error)
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
def dashboard(request, subdomain):
    """廠商Dashboard概覽頁面"""

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
def domain_settings(request, subdomain):
    if request.method == "POST":
        form = domain_settings_form(request.POST, instance=request.merchant)
        if form.is_valid():
            update_merchant = form.save()
            messages.success(request, "網域名稱已更新")
            return redirect(
                "merchant_account:domain_settings", update_merchant.subdomain
            )
        else:
            messages.error(request, "設定失敗，請檢查內容")
    else:
        form = domain_settings_form(instance=request.merchant)
    return render(request, "merchant_account/domain_settings.html", {"form": form})


@no_cache_required
def transaction_history(request, subdomain):
    """廠商交易記錄頁面"""
    # 查詢該商家的所有交易記錄（使用統一的 Order 模型）
    orders = (
        Order.objects.select_related("customer", "product")
        .prefetch_related("items")  # 預載入票券資料
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


# === 票券驗證相關視圖 ===


@no_cache_required
def ticket_validation_page(request, subdomain):
    """票券驗證主頁面"""
    return render(request, "merchant_account/ticket_validation.html")


@no_cache_required
@require_POST
def validate_ticket(request, subdomain):
    """驗證票券（手動輸入驗證碼或QR掃描）"""
    merchant = request.merchant
    ticket_code = request.POST.get("ticket_code", "").strip().upper()
    validation_method = request.POST.get("method", "manual")

    # 記錄驗證嘗試
    def create_validation_record(ticket, status, reason=""):
        return TicketValidation.objects.create(
            ticket=ticket,
            merchant=merchant,
            status=status,
            failure_reason=reason,
            validation_method=validation_method,
            ip_address=request.META.get("REMOTE_ADDR"),
        )

    if not ticket_code:
        context = {
            "error_message": "請輸入票券驗證碼",
            "merchant": merchant,
        }
        return render(request, "merchant_account/partials/ticket_error.html", context)

    try:
        # 查找票券（OrderItem）
        ticket = OrderItem.objects.select_related(
            "order", "product__merchant", "customer"
        ).get(ticket_code=ticket_code)

        # 檢查票券有效性和商家權限
        is_valid, message = ticket.is_valid()
        if not is_valid:
            create_validation_record(ticket, "failed", message)
            context = {
                "error_message": message,
                "merchant": merchant,
            }
            return render(
                request, "merchant_account/partials/ticket_error.html", context
            )

        # 檢查商家權限
        if ticket.product.merchant != merchant:
            create_validation_record(ticket, "unauthorized", "您無權限驗證此票券")
            context = {
                "error_message": "您無權限驗證此票券",
                "merchant": merchant,
            }
            return render(
                request, "merchant_account/partials/ticket_error.html", context
            )

        # 票券驗證成功，顯示確認頁面（驗證不需記錄，只有實際使用才記錄）
        context = {
            "ticket_code": ticket_code,
            "ticket_info": ticket.ticket_info,
            "merchant": merchant,
        }
        return render(request, "merchant_account/partials/ticket_success.html", context)

    except OrderItem.DoesNotExist:
        # 找不到票券
        context = {
            "error_message": "找不到此票券代碼",
            "merchant": merchant,
        }
        return render(request, "merchant_account/partials/ticket_error.html", context)


@no_cache_required
@require_POST
def use_ticket(request, subdomain):
    """確認使用票券"""
    merchant = request.merchant
    ticket_code = request.POST.get("ticket_code", "").strip().upper()

    if not ticket_code:
        context = {
            "error_message": "票券代碼遺失",
            "merchant": merchant,
        }
        return render(request, "merchant_account/partials/ticket_error.html", context)

    try:
        ticket = OrderItem.objects.select_related(
            "order", "product__merchant", "customer"
        ).get(ticket_code=ticket_code)

        # 使用票券
        success, message = ticket.use_ticket(merchant)

        if success:
            # ticket.use_ticket() 已經更新票券狀態到資料庫，不需要額外記錄

            context = {
                "message": message,
                "ticket_value": ticket.order.unit_price,
                "used_at": ticket.used_at,
                "merchant": merchant,
            }
            return render(
                request, "merchant_account/partials/ticket_used.html", context
            )
        else:
            context = {
                "error_message": message,
                "merchant": merchant,
            }
            return render(
                request, "merchant_account/partials/ticket_error.html", context
            )

    except OrderItem.DoesNotExist:
        context = {
            "error_message": "找不到此票券代碼",
            "merchant": merchant,
        }
        return render(request, "merchant_account/partials/ticket_error.html", context)


@no_cache_required
@require_POST
def restart_scan(request, subdomain):
    """重新開始掃描"""
    context = {}
    return render(request, "merchant_account/partials/scan_ready.html", context)
