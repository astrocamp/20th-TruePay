from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.utils import timezone

from .models import Payment
from .utils import NewebPayUtils



@login_required
def create_payment(request):
    """建立付款訂單視圖 - 需要登入"""
    if request.method == "POST":
        # 取得付款資訊
        amt_str = request.POST.get("amt", "0")
        try:
            # 將字串轉為浮點數再轉為整數（藍新金流需要整數金額）
            amt = int(float(amt_str))
        except (ValueError, TypeError):
            return JsonResponse({"error": "金額格式錯誤"}, status=400)
            
        item_desc = request.POST.get("item_desc", "測試商品")
        # 使用登入用戶的資訊
        email = request.user.email or ""
        customer_name = request.user.get_full_name() or request.user.username

        if amt <= 0:
            return JsonResponse({"error": "金額必須大於 0"}, status=400)

        # 建立付款記錄
        payment = Payment.objects.create(
            amt=amt,
            item_desc=item_desc,
            email=email,
            customer_name=customer_name,
            status="pending",
        )

        # 使用 NewebPay 工具類產生付款表單
        newebpay = NewebPayUtils()
        payment_data = {
            "merchant_order_no": payment.merchant_order_no,
            "amt": payment.amt,
            "item_desc": payment.item_desc,
            "email": payment.email,
        }

        form_data = newebpay.create_payment_form_data(payment_data)

        # 返回付款表單資料
        context = {
            "form_data": form_data,
            "gateway_url": settings.CURRENT_GATEWAY_URL,
            "payment": payment,
        }

        return render(request, "newebpay/payment_form.html", context)

    return redirect("pages:home")


@login_required
def payment_status(request, payment_id):
    """查詢付款狀態 - 需要登入且只能查看自己的訂單"""
    payment = get_object_or_404(Payment, id=payment_id)
    
    # 確保用戶只能查看自己的付款記錄
    # 這裡需要在 Payment 模型中添加 user 欄位來關聯用戶
    # 暫時先允許所有已登入用戶查看（後續可以改進）

    context = {
        "payment": payment,
    }

    return render(request, "newebpay/payment_status.html", context)


@csrf_exempt
def payment_return(request):
    """付款完成返回頁面 - 用戶會看到這個頁面"""
    if request.method == "POST":
        # 取得藍新回傳的資料
        trade_info = request.POST.get("TradeInfo")
        trade_sha = request.POST.get("TradeSha")

        print(f"Return 收到的完整 POST 資料: {dict(request.POST)}")
        print(f"Return TradeInfo 長度: {len(trade_info) if trade_info else 0}")
        print(f"Return TradeSha: {trade_sha}")

        if not trade_info or not trade_sha:
            return render(
                request,
                "newebpay/payment_result.html",
                {"success": False, "message": "付款資料不完整"},
            )

        # 嘗試驗證資料完整性
        newebpay = NewebPayUtils()
        is_valid, result = newebpay.verify_notify_data(
            {"TradeInfo": trade_info, "TradeSha": trade_sha}
        )

        if is_valid:
            # 解密成功，使用解密後的資料
            if isinstance(result, dict) and "Result" in result:
                merchant_order_no = result["Result"].get("MerchantOrderNo", "")
            else:
                merchant_order_no = (
                    result.get("MerchantOrderNo", [""])[0]
                    if isinstance(result.get("MerchantOrderNo"), list)
                    else result.get("MerchantOrderNo", "")
                )

            try:
                payment = Payment.objects.get(merchant_order_no=merchant_order_no)
                payment.return_received = True
                payment.save()

                return render(
                    request,
                    "newebpay/payment_result.html",
                    {"success": True, "payment": payment, "message": "付款處理完成"},
                )
            except Payment.DoesNotExist:
                pass  # 找不到訂單，繼續嘗試其他方法

        # 如果解密失敗或找不到訂單，記錄錯誤並顯示明確訊息
        import logging
        from django.utils import timezone
        logger = logging.getLogger(__name__)
        
        error_info = {
            "trade_info_length": len(trade_info) if trade_info else 0,
            "trade_sha": trade_sha,
            "decrypt_result": result if not is_valid else "N/A",
            "user_ip": request.META.get('REMOTE_ADDR'),
            "timestamp": timezone.now().isoformat()
        }
        
        logger.error(f"付款回調驗證失敗: {error_info}")
        
        return render(
            request,
            "newebpay/payment_result.html",
            {
                "success": False,
                "message": "付款資料驗證失敗。如果您已完成付款，請聯繫客服並提供訂單資訊以協助查詢。",
                "support_info": "客服將協助您確認付款狀態並處理相關事宜。"
            },
        )

    return render(
        request,
        "newebpay/payment_result.html",
        {"success": False, "message": "無效的請求方式"},
    )


@csrf_exempt
def payment_notify(request):
    """藍新後台通知 - 更新付款狀態的核心邏輯"""
    if request.method == "POST":
        try:
            # 取得藍新回傳的資料
            trade_info = request.POST.get("TradeInfo")
            trade_sha = request.POST.get("TradeSha")

            print(f"收到藍新通知 - TradeInfo: {trade_info}")
            print(f"收到藍新通知 - TradeSha: {trade_sha}")

            if not trade_info or not trade_sha:
                return HttpResponse("missing parameters", status=400)

            # 驗證資料完整性
            newebpay = NewebPayUtils()
            is_valid, result = newebpay.verify_notify_data(
                {"TradeInfo": trade_info, "TradeSha": trade_sha}
            )

            if not is_valid:
                print(f"資料驗證失敗: {result}")
                return HttpResponse("validation failed", status=400)

            print(f"解密後的資料: {result}")

            # 更新付款記錄
            if isinstance(result, dict) and "Result" in result:
                # JSON 格式回傳
                merchant_order_no = result["Result"].get("MerchantOrderNo", "")
                status = result.get("Status", "")
                result_data = result["Result"]
            else:
                # Query string 格式回傳
                merchant_order_no = (
                    result.get("MerchantOrderNo", [""])[0]
                    if isinstance(result.get("MerchantOrderNo"), list)
                    else result.get("MerchantOrderNo", "")
                )
                status = (
                    result.get("Status", [""])[0]
                    if isinstance(result.get("Status"), list)
                    else result.get("Status", "")
                )
                result_data = result

            payment = Payment.objects.get(merchant_order_no=merchant_order_no)

            # 更新付款狀態
            if status == "SUCCESS":
                payment.status = "paid"
                payment.trade_no = result_data.get("TradeNo", "")
                payment.payment_type = result_data.get("PaymentType", "")
                payment.pay_time = timezone.now()

                # 信用卡相關資訊
                if "AuthBank" in result_data:
                    payment.auth_bank = result_data.get("AuthBank", "")
                if "RespondCode" in result_data:
                    payment.respond_code = result_data.get("RespondCode", "")
                if "Auth" in result_data:
                    payment.auth = result_data.get("Auth", "")
                if "Card6No" in result_data:
                    payment.card_6no = result_data.get("Card6No", "")
                if "Card4No" in result_data:
                    payment.card_4no = result_data.get("Card4No", "")
            else:
                payment.status = "failed"

            # 標記已收到後台通知並儲存原始資料
            payment.notify_received = True
            payment.notify_data = dict(result)
            payment.save()

            print(f"付款狀態已更新: {payment.merchant_order_no} -> {payment.status}")

            # 回傳 SUCCESS 給藍新金流
            return HttpResponse("1|OK")

        except Payment.DoesNotExist:
            print(f"找不到訂單: {merchant_order_no}")
            return HttpResponse("order not found", status=404)
        except Exception as e:
            print(f"處理通知時發生錯誤: {e}")
            return HttpResponse("server error", status=500)

    return HttpResponse("invalid method", status=405)


def payment_cancel(request):
    """付款取消頁面"""
    return render(request, "newebpay/payment_cancel.html")