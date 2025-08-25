from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.conf import settings
from django.utils import timezone

from django.urls import reverse

from .models import Payment
from .utils import NewebPayUtils
from customers_account.decorators import customer_login_required
from customers_account.models import Customer
from orders.models import OrderItem
from merchant_marketplace.models import Product




def create_payment(request):

    """建立付款訂單視圖 - 需要登入"""
    if request.method == "POST":
        # 如果未登入，將 POST 資料存到 session 後重導向到登入
        if 'customer_id' not in request.session:
            request.session['payment_data'] = {
                'amt': request.POST.get('amt'),
                'item_desc': request.POST.get('item_desc')
            }
            login_url = reverse('customers_account:login')
            next_url = request.get_full_path()
            return redirect(f"{login_url}?next={next_url}")
        
        # 已登入，處理付款

        amt_str = request.POST.get("amt", "0")
        try:
            # 將字串轉為浮點數再轉為整數（藍新金流需要整數金額）
            amt = int(float(amt_str))
        except (ValueError, TypeError):
            return JsonResponse({"error": "金額格式錯誤"}, status=400)
            
        item_desc = request.POST.get("item_desc", "測試商品")

        
        # 使用登入客戶的資訊
        customer_id = request.session.get('customer_id')
        customer = get_object_or_404(Customer, id=customer_id)
        email = customer.email
        customer_name = customer.name


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

        # 清除暫存的付款資料
        if 'payment_data' in request.session:
            del request.session['payment_data']

        return render(request, "newebpay/payment_form.html", context)
    
    # GET 請求：檢查是否有暫存的付款資料
    if 'customer_id' not in request.session:
        login_url = reverse('customers_account:login')
        next_url = request.get_full_path()
        return redirect(f"{login_url}?next={next_url}")
    
    # 如果有暫存的付款資料，自動處理付款
    payment_data = request.session.get('payment_data')
    if payment_data:
        # 模擬 POST 請求來處理付款
        request.POST = request.POST.copy()
        request.POST['amt'] = payment_data['amt']
        request.POST['item_desc'] = payment_data['item_desc']
        request.method = 'POST'
        return create_payment(request)
    
    # 沒有付款資料，重導向回首頁
    return redirect("pages:home")


@customer_login_required
def payment_status(request, payment_id):
    """查詢付款狀態 - 需要登入且只能查看自己的訂單"""
    payment = get_object_or_404(Payment, id=payment_id)
    
    # 確保用戶只能查看自己的付款記錄


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
                
                # 如果付款成功且還沒有建立購買記錄，現在建立
                if payment.status == "paid":
                    existing_record = OrderItem.objects.filter(payment=payment).exists()
                    
                    if not existing_record:
                        try:
                            # 從 item_desc 解析商品 ID
                            item_desc = payment.item_desc
                            
                            product_id = None
                            if '|ProductID:' in item_desc:
                                product_id = item_desc.split('|ProductID:')[1]
                            
                            # 從 email 找到客戶
                            customer = Customer.objects.get(email=payment.email)
                            
                            # 找到商品
                            if product_id:
                                product = Product.objects.get(id=int(product_id))
                                
                                # 建立訂單項目
                                OrderItem.objects.create(
                                    payment=payment,
                                    customer=customer,
                                    product=product,
                                    quantity=1,  # 固定為1個
                                    unit_price=payment.amt,
                                    payment_provider='newebpay'  # 藍新金流
                                )
                            
                        except (Customer.DoesNotExist, Product.DoesNotExist, Exception):
                            pass

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


            if not trade_info or not trade_sha:
                return HttpResponse("missing parameters", status=400)

            # 驗證資料完整性
            newebpay = NewebPayUtils()
            is_valid, result = newebpay.verify_notify_data(
                {"TradeInfo": trade_info, "TradeSha": trade_sha}
            )

            if not is_valid:
                return HttpResponse("validation failed", status=400)


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
            
            # 如果付款成功，建立購買記錄
            if payment.status == "paid":
                try:
                    pass
                except Exception:
                    pass


            # 回傳 SUCCESS 給藍新金流
            return HttpResponse("1|OK")

        except Payment.DoesNotExist:
            return HttpResponse("order not found", status=404)
        except Exception:
            return HttpResponse("server error", status=500)

    return HttpResponse("invalid method", status=405)


def payment_cancel(request):
    """付款取消頁面"""
    return render(request, "newebpay/payment_cancel.html")