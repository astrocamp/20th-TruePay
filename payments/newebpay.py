import hashlib
import base64
import json
import logging
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
from django.shortcuts import get_object_or_404
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.utils import timezone
from django.shortcuts import render
from django.contrib.auth import login as django_login
from django.contrib.auth.models import User

from .models import Order

logger = logging.getLogger(__name__)


def process_newebpay(order, request):
    """處理藍新金流付款"""
    try:
        # 藍新金流設定
        merchant_id = settings.NEWEBPAY_MERCHANT_ID
        hash_key = settings.NEWEBPAY_HASH_KEY
        hash_iv = settings.NEWEBPAY_HASH_IV

        # 準備付款資料
        trade_info_data = {
            "MerchantID": merchant_id,
            "RespondType": "JSON",
            "TimeStamp": str(int(order.created_at.timestamp())),
            "Version": "2.0",
            "MerchantOrderNo": order.provider_order_id,  # 使用短格式訂單編號
            "Amt": str(int(order.amount)),
            "ItemDesc": order.item_description,
            "ReturnURL": settings.PAYMENT_RETURN_URL,
            "NotifyURL": settings.PAYMENT_NOTIFY_URL,
            "Email": order.customer.email,
        }

        # 生成 TradeInfo 和 TradeSha
        trade_info_str = "&".join([f"{k}={v}" for k, v in trade_info_data.items()])

        trade_info = aes_encrypt(trade_info_str, hash_key, hash_iv)
        trade_sha = generate_sha256(f"HashKey={hash_key}&{trade_info}&HashIV={hash_iv}")

        # 準備模板資料
        form_data = {
            "MerchantID": merchant_id,
            "TradeInfo": trade_info,
            "TradeSha": trade_sha,
            "Version": "2.0",
        }

        context = {
            "order": order,
            "gateway_url": settings.NEWEBPAY_GATEWAY_URL,
            "form_data": form_data,
        }

        return render(request, "payments/newebpay/payment_form.html", context)

    except Exception as e:
        logger.error(f"藍新金流處理失敗: {e}")
        from django.http import JsonResponse

        return JsonResponse({"error": "藍新金流處理失敗"}, status=500)


@csrf_exempt
def newebpay_return(request):
    """藍新金流付款完成返回處理"""
    try:
        trade_info = request.POST.get("TradeInfo")
        trade_sha = request.POST.get("TradeSha")

        # 解密交易資料
        hash_key = settings.NEWEBPAY_HASH_KEY
        hash_iv = settings.NEWEBPAY_HASH_IV

        # 驗證簽名
        check_value = generate_sha256(
            f"HashKey={hash_key}&{trade_info}&HashIV={hash_iv}"
        )
        if check_value.upper() != trade_sha.upper():
            logger.error(
                f"簽名驗證失敗 - Expected: {check_value.upper()}, Got: {trade_sha.upper()}"
            )
            from django.shortcuts import render

            return render(
                request,
                "payments/newebpay/payment_result.html",
                {"success": False, "message": "簽名驗證失敗"},
            )

        # 解密資料
        decrypted_data = aes_decrypt(trade_info, hash_key, hash_iv)
        result_data = json.loads(decrypted_data)

        if result_data["Status"] == "SUCCESS":
            # 更新付款狀態
            merchant_order_no = result_data["Result"]["MerchantOrderNo"]
            order = get_object_or_404(Order, provider_order_id=merchant_order_no)
            order.status = "paid"
            order.provider_transaction_id = result_data["Result"]["TradeNo"]
            order.newebpay_trade_no = result_data["Result"]["TradeNo"]

            # 儲存詳細付款資訊 (如果有的話)
            result = result_data["Result"]
            if "PaymentType" in result:
                order.newebpay_payment_type = result["PaymentType"]
            # 藍新金流的卡號資訊直接在 Result 層級
            if "Card6No" in result and "Card4No" in result:
                order.newebpay_card_info = (
                    f"{result['Card6No']}******{result['Card4No']}"
                )

            # 儲存完整原始資料
            order.provider_raw_data = result_data
            order.paid_at = timezone.now()
            order.save()

            # 付款成功後恢復用戶登入狀態（金流回調不攜帶 session）
            if order.customer:
                try:
                    # 根據訂單客戶資訊建立對應的 Django User session
                    user, created = User.objects.get_or_create(
                        username=order.customer.email,
                        defaults={
                            'email': order.customer.email,
                            'first_name': order.customer.name,
                            'is_active': order.customer.account_status == 'active'
                        }
                    )
                    # 建立用戶認證 session
                    django_login(request, user)
                    logger.info(f"藍新金流付款成功，已為用戶 {order.customer.email} 恢復登入狀態")
                except Exception as e:
                    logger.warning(f"藍新金流付款成功後恢復登入狀態失敗: {e}")

            from django.shortcuts import render

            return render(
                request,
                "payments/newebpay/payment_success.html",
                {"success": True, "order": order, "message": "付款成功"},
            )
        else:
            from django.shortcuts import render

            return render(
                request,
                "payments/newebpay/payment_result.html",
                {"success": False, "message": result_data.get("Message", "付款失敗")},
            )

    except Exception as e:
        logger.error(f"藍新金流回調處理失敗: {e}")
        from django.shortcuts import render

        return render(
            request,
            "payments/newebpay/payment_result.html",
            {"success": False, "message": "付款處理失敗"},
        )


@csrf_exempt
def newebpay_notify(request):
    """藍新金流後台通知處理"""
    try:
        # 接收通知資料
        trade_info = request.POST.get("TradeInfo")
        trade_sha = request.POST.get("TradeSha")

        if not trade_info:
            logger.error("藍新金流通知缺少 TradeInfo")
            return HttpResponse("0|Missing TradeInfo")

        hash_key = settings.NEWEBPAY_HASH_KEY
        hash_iv = settings.NEWEBPAY_HASH_IV

        if not hash_key or not hash_iv:
            logger.error("藍新金流設定不完整 - 缺少 hash_key 或 hash_iv")
            return HttpResponse("0|Config Error")

        # 如果有 TradeSha，先驗證簽名
        if trade_sha:
            check_value = generate_sha256(
                f"HashKey={hash_key}&{trade_info}&HashIV={hash_iv}"
            )
            if check_value.upper() != trade_sha.upper():
                logger.error(
                    f"藍新金流通知簽名驗證失敗 - Expected: {check_value.upper()}, Got: {trade_sha.upper()}"
                )
                return HttpResponse("0|Invalid Signature")

        # 嘗試解密
        try:
            decrypted_data = aes_decrypt(trade_info, hash_key, hash_iv)
        except Exception as decrypt_error:
            logger.error(f"AES 解密失敗: {decrypt_error}")
            return HttpResponse("0|Decrypt Error")

        # 解析 JSON 資料
        try:
            result_data = json.loads(decrypted_data)
        except json.JSONDecodeError as json_error:
            logger.error(f"JSON 解析失敗: {json_error}")
            return HttpResponse("0|JSON Parse Error")

        # 處理付款結果
        if result_data.get("Status") == "SUCCESS":
            try:
                merchant_order_no = result_data["Result"]["MerchantOrderNo"]
                order = Order.objects.get(provider_order_id=merchant_order_no)

                if order.status == "pending":
                    order.status = "paid"
                    order.provider_transaction_id = result_data["Result"]["TradeNo"]
                    order.newebpay_trade_no = result_data["Result"]["TradeNo"]

                    # 儲存詳細付款資訊 (如果有的話)
                    result = result_data["Result"]

                    if "PaymentType" in result:
                        order.newebpay_payment_type = result["PaymentType"]

                    # 藍新金流的卡號資訊直接在 Result 層級，不是在 CardInfo 子物件
                    if "Card6No" in result and "Card4No" in result:
                        order.newebpay_card_info = (
                            f"{result['Card6No']}******{result['Card4No']}"
                        )

                    # 儲存完整原始資料
                    order.provider_raw_data = result_data
                    order.paid_at = timezone.now()
                    order.save()

                    logger.info(
                        f"藍新金流通知處理成功 - 訂單 {merchant_order_no} 已更新為已付款"
                    )

                return HttpResponse("1|OK")

            except Order.DoesNotExist:
                logger.error(f"藍新金流通知 - 找不到訂單: {merchant_order_no}")
                return HttpResponse("0|Order Not Found")
            except Exception as order_error:
                logger.error(f"藍新金流通知處理訂單時發生錯誤: {order_error}")
                return HttpResponse("0|Order Update Error")
        else:
            logger.warning(f"藍新金流通知 - 付款失敗: {result_data}")
            return HttpResponse("0|Payment Failed")

    except Exception as e:
        logger.error(f"藍新金流通知處理失敗: {e}")
        return HttpResponse("0|System Error")


# 工具函數
def aes_encrypt(data, key, iv):
    """AES 加密 - 藍新金流使用十六進制格式"""
    cipher = AES.new(key.encode("utf-8"), AES.MODE_CBC, iv.encode("utf-8"))
    padded_data = pad(data.encode("utf-8"), AES.block_size)
    encrypted_data = cipher.encrypt(padded_data)
    return encrypted_data.hex()  # 使用十六進制，不是 Base64


def aes_decrypt(encrypted_data, key, iv):
    """AES 解密 - 自動檢測編碼格式"""
    cipher = AES.new(key.encode("utf-8"), AES.MODE_CBC, iv.encode("utf-8"))

    # 先嘗試十六進制解碼（發送給藍新的格式）
    try:
        decrypted_data = cipher.decrypt(bytes.fromhex(encrypted_data))
        result = unpad(decrypted_data, AES.block_size).decode("utf-8")
        return result
    except (ValueError, Exception):
        pass

    # 如果失敗，嘗試 Base64 解碼（回調可能使用的格式）
    try:
        decrypted_data = cipher.decrypt(base64.b64decode(encrypted_data))
        result = unpad(decrypted_data, AES.block_size).decode("utf-8")
        return result
    except (ValueError, Exception):
        pass

    # 如果兩種方式都失敗，嘗試直接解碼（以防是其他格式）
    try:
        decrypted_data = cipher.decrypt(encrypted_data.encode("utf-8"))
        result = unpad(decrypted_data, AES.block_size).decode("utf-8")
        return result
    except Exception:
        pass

    # 所有方法都失敗，記錄一次錯誤日誌
    logger.error("AES 解密失敗 - 所有解密方法都無法解密資料")
    raise ValueError("所有解密方法都失敗了 - 可能是加密格式、Key 或 IV 不正確")


def generate_sha256(data):
    """生成 SHA256"""
    return hashlib.sha256(data.encode("utf-8")).hexdigest().upper()
