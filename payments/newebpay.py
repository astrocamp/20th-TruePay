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
        # 取得商家金流設定
        merchant = order.product.merchant
        
        # 優先使用商家個人設定，沒有則使用系統預設
        if merchant.has_newebpay_setup():
            payment_keys = merchant.get_payment_keys()
            merchant_id = payment_keys['newebpay_merchant_id']
            hash_key = payment_keys['newebpay_hash_key']
            hash_iv = payment_keys['newebpay_hash_iv']
            logger.info(f"使用商家 {merchant.ShopName} 的個人金流設定")
        else:
            # 使用系統預設設定
            merchant_id = settings.NEWEBPAY_MERCHANT_ID
            hash_key = settings.NEWEBPAY_HASH_KEY
            hash_iv = settings.NEWEBPAY_HASH_IV
            logger.info(f"商家 {merchant.ShopName} 未設定個人金流，使用系統預設")

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

        # 使用高效解密方法
        result_data, hash_key, hash_iv = decrypt_newebpay_callback(trade_info, trade_sha)

        # 如果解密失敗
        if not result_data:
            logger.error("無法解密回調資料")
            from django.shortcuts import render
            return render(
                request,
                "payments/newebpay/payment_result.html",
                {"success": False, "message": "簽名驗證失敗"},
            )

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

        # 使用高效解密方法
        result_data, hash_key, hash_iv = decrypt_newebpay_callback(trade_info, trade_sha)

        # 如果解密失敗
        if not result_data:
            logger.error("無法解密通知資料")
            return HttpResponse("0|Decrypt Error")

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


def decrypt_newebpay_callback(trade_info, trade_sha=None):
    """
    解密藍新金流回調資料
    先用系統預設金鑰解密取得 MerchantID，再用對應商家金鑰驗證
    """
    from merchant_account.models import Merchant
    
    # 步驟1: 先用系統預設金鑰解密，取得 MerchantID
    system_hash_key = settings.NEWEBPAY_HASH_KEY
    system_hash_iv = settings.NEWEBPAY_HASH_IV
    
    if not system_hash_key or not system_hash_iv:
        logger.error("系統預設金鑰配置不完整")
        return None, None, None
    
    try:
        # 嘗試用系統預設金鑰解密，取得基本資訊
        decrypted_data = aes_decrypt(trade_info, system_hash_key, system_hash_iv)
        basic_data = json.loads(decrypted_data)
        
        # 取得 MerchantID
        merchant_id = basic_data.get("MerchantID") or basic_data.get("Result", {}).get("MerchantID")
        if not merchant_id:
            logger.error("無法從解密資料中取得 MerchantID")
            return None, None, None
            
        logger.info(f"從回調資料中識別出 MerchantID: {merchant_id}")
        
        # 步驟2: 根據 MerchantID 查詢對應商家
        try:
            merchant = Merchant.objects.get(newebpay_merchant_id=merchant_id)
            if not merchant.has_newebpay_setup():
                logger.warning(f"商家 {merchant.ShopName} 的藍新金流未完整設定")
                # 如果商家金鑰未設定，使用系統預設金鑰
                return _verify_and_return(trade_info, trade_sha, system_hash_key, system_hash_iv, "系統預設", basic_data)
            
            # 步驟3: 使用商家專屬金鑰重新解密並驗證
            payment_keys = merchant.get_payment_keys()
            merchant_hash_key = payment_keys['newebpay_hash_key']
            merchant_hash_iv = payment_keys['newebpay_hash_iv']
            
            return _verify_and_return(trade_info, trade_sha, merchant_hash_key, merchant_hash_iv, f"商家 {merchant.ShopName}", None)
            
        except Merchant.DoesNotExist:
            logger.warning(f"找不到 MerchantID 為 {merchant_id} 的商家，使用系統預設金鑰")
            # 找不到商家時，使用系統預設金鑰
            return _verify_and_return(trade_info, trade_sha, system_hash_key, system_hash_iv, "系統預設", basic_data)
            
    except Exception as e:
        logger.error(f"解密回調資料失敗: {e}")
        return None, None, None


def _verify_and_return(trade_info, trade_sha, hash_key, hash_iv, key_source, cached_data=None):
    """驗證簽名並返回解密結果"""
    try:
        # 如果有快取的解密資料且不需要簽名驗證，直接使用
        if cached_data and not trade_sha:
            logger.info(f"使用{key_source}金鑰成功解密回調（無簽名）")
            return cached_data, hash_key, hash_iv
        
        # 驗證簽名（如果有）
        if trade_sha:
            check_value = generate_sha256(f"HashKey={hash_key}&{trade_info}&HashIV={hash_iv}")
            if check_value.upper() != trade_sha.upper():
                logger.warning(f"{key_source}金鑰簽名驗證失敗")
                return None, None, None
        
        # 重新解密（或使用快取）
        if cached_data:
            result_data = cached_data
        else:
            decrypted_data = aes_decrypt(trade_info, hash_key, hash_iv)
            result_data = json.loads(decrypted_data)
        
        logger.info(f"使用{key_source}金鑰成功解密回調")
        return result_data, hash_key, hash_iv
        
    except Exception as e:
        logger.error(f"{key_source}金鑰解密失敗: {e}")
        return None, None, None


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
