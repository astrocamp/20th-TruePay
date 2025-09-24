# Standard library imports
import json
from functools import wraps
from urllib.parse import urlparse

# Third party imports
import pyotp

# Django imports
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model, login as django_login, logout as django_logout, update_session_auth_hash
from django.core.mail import send_mail
from django.core.paginator import Paginator
from django.core.signing import TimestampSigner, BadSignature, SignatureExpired
from django.db import transaction
from django.db.models import Sum, Q, Count
from django.http import Http404, HttpResponseRedirect, JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_http_methods

# Local imports
from truepay.decorators import customer_login_required
from .forms import (
    CustomerRegistrationForm,
    CustomerLoginForm,
    CustomerProfileUpdateForm,
    PasswordChangeForm,
    ForgotPasswordForm,
    PasswordResetForm,
)
from .models import Customer
from payments.models import Order, OrderItem
from merchant_account.models import Merchant


def register(request):
    # 檢查用戶是否已經登入
    if (
        request.user.is_authenticated
        and hasattr(request.user, "member_type")
        and request.user.member_type == "customer"
    ):
        messages.info(request, "您已經註冊並登入了")
        return redirect("pages:marketplace")

    if request.method == "POST":
        form = CustomerRegistrationForm(request.POST)
        if form.is_valid():
            try:
                customer = form.save()
                # 自動登入新註冊的用戶
                django_login(request, customer.member, backend="django.contrib.auth.backends.ModelBackend")
                messages.success(request, "註冊成功！歡迎加入 TruePay！")
                # 跳轉到 Google Authenticator 下載引導頁面
                return redirect("customers_account:authenticator_guide")
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
    # 檢查用戶是否已經登入
    if (
        request.user.is_authenticated
        and hasattr(request.user, "member_type")
        and request.user.member_type == "customer"
    ):
        messages.info(request, "您已經登入了")
        return redirect("pages:marketplace")

    if request.method == "POST":
        form = CustomerLoginForm(request.POST)
        if form.is_valid():
            member = form.cleaned_data["member"]

            # 使用 Django 認證系統登入
            django_login(
                request, member, backend="django.contrib.auth.backends.ModelBackend"
            )

            # 檢查是否有 next 參數（登入後要重導向的頁面）
            next_url = request.GET.get("next") or request.POST.get("next")
            if next_url:
                messages.success(request, "登入成功")
                parsed_url = urlparse(next_url)
                if parsed_url.netloc and not parsed_url.netloc.endswith(
                    settings.BASE_DOMAIN
                ):
                    return redirect("customers_account:dashboard")
                return HttpResponseRedirect(next_url)
            else:
                messages.success(request, "登入成功")
                return redirect("pages:marketplace")  # 跳轉到商品總覽
        else:
            for error in form.non_field_errors():
                messages.error(request, error)
    else:
        form = CustomerLoginForm()

    return render(request, "customers/login.html", {"form": form})


def logout(request):
    # 檢查用戶是否已經登入
    if not request.user.is_authenticated:
        messages.warning(request, "您尚未登入")
        return redirect("customers_account:login")

    # 檢查是否為客戶用戶
    if (
        not hasattr(request.user, "member_type")
        or request.user.member_type != "customer"
    ):
        messages.error(request, "權限不足")
        return redirect("customers_account:login")

    # 使用 Django 登出（這會清除 session 中的認證資訊）
    django_logout(request)

    # 完全清除 session 並重新生成 session key
    request.session.flush()

    # 注意：由於已經清除了 session，登出訊息將無法儲存
    # 改為在目標頁面使用 URL 參數或其他方式顯示登出訊息

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
    total_amount = (
        orders.filter(status="paid").aggregate(total=Sum("amount"))["total"] or 0
    )
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
    status_filter = request.GET.get("status", "")
    merchant_filter = request.GET.get("merchant", "")
    order_filter = request.GET.get("order", "")

    # 先將已過期且未標記的票券狀態更新為 expired（避免每次模板內判斷）
    now = timezone.now()
    OrderItem.objects.filter(
        customer=customer, status="unused", valid_until__lt=now
    ).update(status="expired")

    # 基本查詢：取得該客戶的所有票券
    tickets = (
        OrderItem.objects.select_related("product__merchant", "order")
        .filter(customer=customer)
        .order_by("-created_at")
    )

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
        total=Count("id"),
        unused=Count("id", filter=Q(status="unused")),
        used=Count("id", filter=Q(status="used")),
        expired=Count("id", filter=Q(status="unused", valid_until__lt=now)),
    )

    # 取得所有相關商家（用於篩選下拉選單）
    merchants = (
        Merchant.objects.filter(product__orderitem__customer=customer)
        .distinct()
        .order_by("ShopName")
    )

    # 分頁處理
    paginator = Paginator(tickets, 10)  # 每頁顯示10筆記錄
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    # 檢查是否已通過核銷前驗證
    redemption_verified = request.session.get("redemption_verified", False)
    redemption_verified_time = request.session.get("redemption_verified_time")

    # 驗證是否在有效時間內（10分鐘）
    is_redemption_verified = False
    if redemption_verified and redemption_verified_time:
        current_time = timezone.now().timestamp()
        if (
            current_time - redemption_verified_time
            <= settings.REDEMPTION_VERIFICATION_TIMEOUT
        ):
            is_redemption_verified = True
        else:
            # 清除過期的驗證狀態
            request.session.pop("redemption_verified", None)
            request.session.pop("redemption_verified_time", None)

    # 檢查是否需要自動展開特定票券的QR Code
    show_qr_ticket_id = request.GET.get("show_qr")

    # 檢查是否來自TOTP驗證成功
    verified_success = request.GET.get("verified") == "success"
    if verified_success and show_qr_ticket_id:
        messages.success(
            request, "✅ 驗證成功！正在跳轉到票券錢包查看 QR Code..."
        )
    elif verified_success:
        messages.success(request, "✅ 驗證成功！正在跳轉到票券錢包...")

    context = {
        "customer": customer,
        "tickets": page_obj,
        "page_obj": page_obj,
        "is_paginated": page_obj.has_other_pages(),
        "ticket_stats": ticket_stats,
        "merchants": merchants,
        "now": now,
        "is_redemption_verified": is_redemption_verified,
        "show_qr_ticket_id": show_qr_ticket_id,
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
            form = CustomerProfileUpdateForm(
                request.POST, instance=customer, user=request.user
            )
            if form.is_valid():
                form.save()
                messages.success(request, "個人資料已成功更新")
                return redirect("customers_account:profile_settings")
            else:
                for field, errors in form.errors.items():
                    for error in errors:
                        messages.error(
                            request,
                            f"{form.fields[field].label if field in form.fields else field}: {error}",
                        )

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
                        messages.error(
                            request,
                            f"{password_form.fields[field].label if field in password_form.fields else field}: {error}",
                        )

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

    # 檢查是否有next參數並驗證URL安全性
    next_url = request.GET.get("next")
    if next_url:
        parsed_url = urlparse(next_url)
        # 只允許相對路徑和同網域的絕對路徑
        if parsed_url.netloc and not parsed_url.netloc.endswith(
            settings.BASE_DOMAIN
        ):
            next_url = None  # 重置為安全的預設值

    context = {
        "customer": customer,
        "qr_code": qr_code,
        "totp_secret": customer.totp_secret_key,
        "next_url": next_url,
    }

    return render(request, "customers/totp_setup.html", context)


@customer_login_required
def totp_enable(request):
    """啟用 TOTP - 驗證用戶輸入的代碼"""
    try:
        customer = Customer.objects.get(member=request.user)
    except Customer.DoesNotExist:
        messages.error(request, "客戶資料不存在")
        return redirect("pages:home")

    if request.method == "POST":
        totp_code = request.POST.get("totp_code", "").strip()

        if not totp_code:
            messages.error(request, "請輸入驗證代碼")
            return redirect("customers_account:totp_setup")

        # 臨時驗證 TOTP 代碼
        if customer.totp_secret_key:
            totp = pyotp.TOTP(customer.totp_secret_key)
            if totp.verify(totp_code, valid_window=1):
                # 驗證成功，啟用 TOTP
                customer.totp_enabled = True
                if not customer.totp_secret_key:
                    customer.generate_totp_secret()
                # 生成備用代碼並獲取明文版本
                backup_tokens = customer.generate_backup_tokens()
                customer.save()

                # 檢查是否有next參數並驗證URL安全性
                next_url = request.GET.get("next") or request.POST.get("next")
                if next_url:
                    parsed_url = urlparse(next_url)
                    # 只允許相對路徑和同網域的絕對路徑
                    if parsed_url.netloc and not parsed_url.netloc.endswith(
                        settings.BASE_DOMAIN
                    ):
                        next_url = None  # 重置為安全的預設值

                messages.success(
                    request, "二階段驗證已成功啟用！請保存您的備用恢復代碼。"
                )
                return render(
                    request,
                    "customers/totp_backup_codes.html",
                    {
                        "customer": customer,
                        "backup_tokens": backup_tokens,
                        "next_url": next_url,
                    },
                )
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
        "customer": customer,
        "backup_tokens": customer.backup_tokens if customer.totp_enabled else [],
    }

    return render(request, "customers/totp_manage.html", context)


@customer_login_required
def totp_disable(request):
    """停用 TOTP"""
    try:
        customer = Customer.objects.get(member=request.user)
    except Customer.DoesNotExist:
        messages.error(request, "客戶資料不存在")
        return redirect("pages:home")

    if request.method == "POST":
        # 要求用戶確認密碼或 TOTP 代碼
        password = request.POST.get("password", "").strip()
        totp_code = request.POST.get("totp_code", "").strip()

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

    if request.method == "POST":
        # 驗證 TOTP 代碼
        totp_code = request.POST.get("totp_code", "").strip()

        if totp_code and customer.verify_totp(totp_code):
            backup_tokens = customer.generate_backup_tokens()
            messages.success(request, "備用恢復代碼已重新生成！請保存新的代碼。")
            return render(
                request,
                "customers/totp_backup_codes.html",
                {
                    "customer": customer,
                    "backup_tokens": backup_tokens,
                    "is_regenerate": True,
                },
            )
        else:
            messages.error(request, "驗證代碼錯誤")

    return redirect("customers_account:totp_manage")


# AJAX API 用於交易過程中驗證 TOTP
@require_http_methods(["POST"])
@customer_login_required
def verify_totp_api(request):
    """API 端點用於驗證 TOTP 代碼"""
    try:
        customer = Customer.objects.get(member=request.user)
        data = json.loads(request.body)
        totp_code = data.get("totp_code", "").strip()

        if not customer.totp_enabled:
            return JsonResponse({"success": False, "error": "二階段驗證未啟用"})

        if not totp_code:
            return JsonResponse({"success": False, "error": "請輸入驗證代碼"})

        if customer.verify_totp(totp_code):
            return JsonResponse({"success": True, "message": "驗證成功"})
        else:
            return JsonResponse({"success": False, "error": "驗證代碼錯誤"})

    except Customer.DoesNotExist:
        return JsonResponse({"success": False, "error": "客戶資料不存在"})
    except json.JSONDecodeError:
        return JsonResponse({"success": False, "error": "無效的請求格式"})
    except Exception as e:
        return JsonResponse({"success": False, "error": "系統錯誤"})


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
                id=order_id, customer=customer
            )

            # 檢查訂單狀態，只能取消待付款的訂單
            if order.status != "pending":
                messages.error(
                    request, f"此訂單狀態為「{order.get_status_display()}」，無法取消"
                )
                return redirect("customers_account:purchase_history")

            # 更新訂單狀態為已取消
            order.status = "cancelled"
            order.save(update_fields=["status", "updated_at"])

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


def forgot_password(request):
    """忘記密碼頁面"""
    if request.method == "POST":
        form = ForgotPasswordForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data["email"]
            # 使用表單中已驗證的 member 物件
            member = form.member

            try:
                # 使用 Django signing 生成重設 token
                signer = TimestampSigner()
                token = signer.sign(str(member.id))

                # 建立重設連結
                reset_url = request.build_absolute_uri(
                    reverse("customers_account:reset_password", kwargs={"token": token})
                )

                # 使用 Django send_mail（就像商家歡迎郵件一樣）
                subject = "TruePay - 密碼重設請求"
                message = f"""
親愛的用戶，

您好！我們收到您的密碼重設請求。

請複製以下連結到瀏覽器中重設您的密碼：
{reset_url}

此連結將在 30 分鐘後過期。

如果您沒有提出此請求，請忽略此郵件。

為保護您的帳號安全，請勿將此連結分享給他人。

祝您使用愉快！
TruePay 團隊
                """

                try:
                    send_mail(
                        subject,
                        message,
                        settings.DEFAULT_FROM_EMAIL,
                        [email],
                        fail_silently=False,
                    )
                    print(f"✅ 密碼重設郵件已發送給 {email}")
                    messages.success(
                        request, "密碼重設連結已發送到您的電子郵件，請檢查收件匣"
                    )

                except Exception as e:
                    print(f"❌ 郵件發送失敗：{e}")
                    messages.error(request, "發送郵件時發生錯誤，請稍後再試")

                return redirect("customers_account:login")

            except Exception as e:
                messages.error(request, f"發送郵件時發生錯誤：{str(e)}")
    else:
        form = ForgotPasswordForm()

    return render(request, "customers/forgot_password.html", {"form": form})


def reset_password(request, token):
    """重設密碼頁面"""
    # 驗證 token
    signer = TimestampSigner()
    try:
        # token 有效期 30 分鐘 (1800 秒)
        user_id = signer.unsign(token, max_age=1800)

        # 取得用戶
        Member = get_user_model()
        member = Member.objects.get(id=int(user_id), member_type="customer")

        if request.method == "POST":
            form = PasswordResetForm(request.POST)
            if form.is_valid():
                # 重設密碼
                new_password = form.cleaned_data["new_password"]
                member.set_password(new_password)
                # 清除登入失敗次數
                member.login_failed_count = 0
                member.save(update_fields=["password", "login_failed_count"])

                messages.success(request, "密碼重設成功！請使用新密碼登入")
                return redirect("customers_account:login")

        else:
            form = PasswordResetForm()

        context = {
            "form": form,
            "token": token,
            "user_email": member.email,
        }
        return render(request, "customers/reset_password.html", context)

    except SignatureExpired:
        messages.error(request, "密碼重設連結已過期，請重新申請")
        return redirect("customers_account:forgot_password")
    except (BadSignature, ValueError, Member.DoesNotExist):
        messages.error(request, "無效的重設連結")
        return redirect("customers_account:forgot_password")


@customer_login_required
def totp_verify_for_redemption(request):
    """核銷前2FA驗證頁面"""
    try:
        customer = Customer.objects.get(member=request.user)
    except Customer.DoesNotExist:
        messages.error(request, "客戶資料不存在")
        return redirect("pages:home")

    if not customer.totp_enabled:
        messages.error(request, "請先啟用二階段驗證")
        return redirect("customers_account:totp_setup")

    # 取得票券資訊
    ticket_id = request.GET.get("ticket_id")
    next_url = request.GET.get("next", reverse("customers_account:ticket_wallet"))

    ticket = None
    if ticket_id:
        try:
            ticket = get_object_or_404(OrderItem, id=ticket_id, customer=customer)
        except Http404:
            messages.error(request, "票券不存在或無權存取")
            return redirect("customers_account:ticket_wallet")

    if request.method == "POST":
        totp_code = request.POST.get("totp_code", "").strip()

        if not totp_code:
            messages.error(request, "請輸入驗證代碼")
        elif len(totp_code) != 6 or not totp_code.isdigit():
            messages.error(request, "驗證代碼格式錯誤")
        elif customer.verify_totp(totp_code):
            # 驗證成功，設定session表示已通過核銷前驗證
            request.session["redemption_verified"] = True
            request.session["redemption_verified_time"] = timezone.now().timestamp()

            if ticket_id:
                # 安全地添加查詢參數，包含驗證成功狀態
                if "?" in next_url:
                    next_url += f"&show_qr={ticket_id}&verified=success"
                else:
                    next_url += f"?show_qr={ticket_id}&verified=success"
            else:
                # 添加驗證成功狀態參數
                if "?" in next_url:
                    next_url += "&verified=success"
                else:
                    next_url += "?verified=success"

            return redirect(next_url)
        else:
            messages.error(
                request,
                "❌ 驗證代碼錯誤！請檢查：\n• 代碼是否為6位數字\n• 代碼是否已過期（每30秒更新）\n• Google Authenticator 時間是否正確",
            )

    context = {
        "customer": customer,
        "ticket": ticket,
        "next_url": next_url,
    }
    return render(request, "customers/totp_verify_for_redemption.html", context)


def customer_required(view_func):
    """確保用戶已登入且為客戶的裝飾器"""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        # 檢查用戶是否已登入
        if not request.user.is_authenticated:
            messages.error(request, "請先登入")
            return redirect("customers_account:login")

        # 檢查是否為客戶
        if not hasattr(request.user, "member_type") or request.user.member_type != "customer":
            messages.error(request, "權限不足")
            return redirect("pages:home")

        # 獲取客戶資料
        try:
            customer = Customer.objects.get(member=request.user)
            # 將客戶資料加入 request 以便 view 使用
            request.customer = customer
        except Customer.DoesNotExist:
            messages.error(request, "客戶資料不存在")
            return redirect("pages:home")

        return view_func(request, *args, **kwargs)
    return wrapper


@customer_required
def authenticator_guide(request):
    """Google Authenticator 下載引導頁面"""
    customer = request.customer  # 由裝飾器提供

    # 如果用戶已經啟用了2FA，直接跳轉到管理頁面
    if customer.totp_enabled:
        messages.info(request, "您已經啟用二階段驗證")
        return redirect("customers_account:totp_manage")

    # 檢查是否有 next 參數並驗證URL安全性，決定是否顯示「稍後再做設定」按鈕
    next_url = request.GET.get("next")
    if next_url:
        parsed_url = urlparse(next_url)
        # 只允許相對路徑和同網域的絕對路徑
        if parsed_url.netloc and not parsed_url.netloc.endswith(
            settings.BASE_DOMAIN
        ):
            next_url = None  # 重置為安全的預設值

    is_required = bool(next_url)  # 如果有 next 參數，表示是必須設定的

    context = {
        "is_required": is_required,
        "next_url": next_url,
    }

    return render(request, "customers/authenticator_guide.html", context)
