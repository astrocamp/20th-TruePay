import base64
import hashlib
import json
import logging
from datetime import timedelta
from urllib.parse import urlencode

from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
from django.conf import settings
from django.contrib.auth import login as django_login
from django.db import transaction
from django.db.models import F
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt

from accounts.models import Member
from .models import Order

logger = logging.getLogger(__name__)


def process_newebpay(order, request):
    """處理藍新金流付款"""
    try:
        # 使用系統統一金流設定
        merchant_id = settings.NEWEBPAY_MERCHANT_ID
        hash_key = settings.NEWEBPAY_HASH_KEY
        hash_iv = settings.NEWEBPAY_HASH_IV

        # 檢測是否為重新付款（使用秒級比較，避免微秒差異）
        time_diff = abs((order.updated_at - order.created_at).total_seconds())
        is_retry = time_diff > 1  # 如果時間差超過1秒，視為重新付款

        # 重新付款時使用當前時間，首次付款使用訂單建立時間
        if is_retry:
            timestamp = str(int(timezone.now().timestamp()))
        else:
            timestamp = str(int(order.created_at.timestamp()))

        # 準備付款資料
        trade_info_data = {
            "MerchantID": merchant_id,
            "RespondType": "JSON",
            "TimeStamp": timestamp,
            "Version": "2.0",
            "MerchantOrderNo": order.provider_order_id,  # 使用短格式訂單編號
            "Amt": str(int(order.amount)),
            "ItemDesc": order.item_description,
            "ReturnURL": settings.PAYMENT_RETURN_URL,
            "NotifyURL": settings.PAYMENT_NOTIFY_URL,
            "Email": order.customer.member.email,
        }

        # 生成 TradeInfo 和 TradeSha
        # trade_info_str = "&".join([f"{k}={v}" for k, v in trade_info_data.items()])
        trade_info_str = urlencode(trade_info_data)

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

        # 檢查是否為庫存不足錯誤
        error_msg = str(e)
        if "庫存不足" in error_msg or "庫存扣減失敗" in error_msg:
            # 嘗試從訂單中獲取必要資訊
            try:
                params = urlencode(
                    {
                        "product_id": order.product.id,
                        "requested_quantity": order.quantity,
                    }
                )
                return redirect(
                    f"{reverse('payments:stock_insufficient_error')}?{params}"
                )
            except:
                pass

        return JsonResponse({"error": "藍新金流處理失敗"}, status=500)


@csrf_exempt
def newebpay_return(request):
    """藍新金流付款完成返回處理"""
    try:
        trade_info = request.POST.get("TradeInfo")
        trade_sha = request.POST.get("TradeSha")

        # 使用系統統一金鑰解密
        result_data = decrypt_newebpay_callback(trade_info, trade_sha)

        # 如果解密失敗，檢查是否有對應的已付款訂單
        if not result_data:
            # 嘗試尋找最近的已付款訂單作為後備方案
            try:
                # 查找最近5分鐘內狀態變為paid的藍新金流訂單
                recent_paid_order = (
                    Order.objects.filter(
                        provider="newebpay",
                        status="paid",
                        paid_at__gte=timezone.now() - timedelta(minutes=5),
                    )
                    .order_by("-paid_at")
                    .first()
                )

                if recent_paid_order:
                    return render(
                        request,
                        "payments/newebpay/payment_success.html",
                        {
                            "success": True,
                            "order": recent_paid_order,
                            "message": "付款成功",
                        },
                    )
            except Exception:
                pass

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

            # 付款成功後扣減庫存
            _deduct_product_stock(order)

            # 付款成功後恢復用戶登入狀態（金流回調不攜帶 session）
            if order.customer:
                try:
                    # 直接使用已存在的 Member 記錄（不要創建新的）
                    member = order.customer.member
                    # 建立用戶認證 session
                    django_login(
                        request,
                        member,
                        backend="django.contrib.auth.backends.ModelBackend",
                    )
                    logger.info(
                        f"藍新金流付款成功，已為用戶 {order.customer.member.email} 恢復登入狀態"
                    )
                except Exception as e:
                    logger.warning(f"藍新金流付款成功後恢復登入狀態失敗: {e}")

            return render(
                request,
                "payments/newebpay/payment_success.html",
                {"success": True, "order": order, "message": "付款成功"},
            )
        else:
            return render(
                request,
                "payments/newebpay/payment_result.html",
                {"success": False, "message": result_data.get("Message", "付款失敗")},
            )

    except Exception as e:
        logger.error(f"藍新金流回調處理失敗: {e}")
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

        # 詳細 log 記錄原始資料
        logger.info(
            f"藍新通知原始資料 - TradeInfo 長度: {len(trade_info) if trade_info else 0}"
        )
        logger.info(f"藍新通知原始資料 - TradeSha: {trade_sha}")
        logger.info(f"藍新通知原始資料 - POST 完整內容: {dict(request.POST)}")

        if not trade_info:
            logger.error("藍新金流通知缺少 TradeInfo")
            return HttpResponse("0|Missing TradeInfo")

        # 使用系統統一金鑰解密
        result_data = decrypt_newebpay_callback(trade_info, trade_sha)

        # 如果解密失敗
        if not result_data:
            logger.error("無法解密通知資料")
            logger.info(
                f"解密失敗的 TradeInfo 內容: {trade_info[:100]}..."
            )  # 只記錄前100字元
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

                    # 付款成功後扣減庫存
                    _deduct_product_stock(order)

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
    """解密藍新金流回調資料"""
    hash_key = settings.NEWEBPAY_HASH_KEY
    hash_iv = settings.NEWEBPAY_HASH_IV

    if not hash_key or not hash_iv:
        logger.error("系統金流配置不完整")
        return None

    try:
        # 驗證簽名（如果有）
        if trade_sha:
            check_value = generate_sha256(
                f"HashKey={hash_key}&{trade_info}&HashIV={hash_iv}"
            )
            if check_value.upper() != trade_sha.upper():
                logger.error("簽名驗證失敗")
                return None

        # 解密資料
        decrypted_data = aes_decrypt(trade_info, hash_key, hash_iv)

        # 清理解密後的資料，移除多餘的字符
        if decrypted_data:
            # 移除可能的 null 字節和額外空白
            decrypted_data = decrypted_data.strip("\x00").strip()

            # 找到第一個完整的JSON結構（更健全的方法）
            brace_count = 0
            first_json_end = 0
            json_started = False

            for i, char in enumerate(decrypted_data):
                if char == "{":
                    json_started = True
                    brace_count += 1
                elif char == "}" and json_started:
                    brace_count -= 1
                    if brace_count == 0:
                        first_json_end = i + 1
                        break

            if first_json_end > 0:
                decrypted_data = decrypted_data[:first_json_end]
                logger.error(f"[DEBUG] 截取JSON後長度: {len(decrypted_data)}")

            # 再次清理可能的尾部字符
            decrypted_data = decrypted_data.rstrip("\x00").rstrip()

            logger.error(f"[DEBUG] 最終清理後的解密資料長度: {len(decrypted_data)}")
            logger.error(
                f"[DEBUG] 最終清理後的解密資料前100字元: {decrypted_data[:100]}"
            )
            logger.error(
                f"[DEBUG] 最終清理後的解密資料後20字元: {decrypted_data[-20:]}"
            )

        result_data = json.loads(decrypted_data)

        logger.info("成功解密藍新金流回調資料")
        return result_data

    except Exception as e:
        logger.error(f"解密回調資料失敗: {e}")
        return None


def _deduct_product_stock(order):
    """扣減商品庫存"""
    try:
        with transaction.atomic():
            product = order.product
            rows_updated = product.__class__.objects.filter(
                id=product.id, stock__gte=order.quantity  # 確保庫存足夠
            ).update(stock=F("stock") - order.quantity)

            if rows_updated == 0:
                error_msg = f"訂單 {order.provider_order_id} 庫存扣減失敗 - 庫存不足或商品不存在"
                logger.error(error_msg)
                raise ValueError(error_msg)
            else:
                logger.info(
                    f"訂單 {order.provider_order_id} 成功扣減 {order.quantity} 件庫存"
                )

    except Exception as e:
        logger.error(f"扣減庫存時發生錯誤: {e}")
        raise


# 工具函數
def aes_encrypt(data, key, iv):
    """AES 加密 - 藍新金流使用十六進制格式"""
    cipher = AES.new(key.encode("utf-8"), AES.MODE_CBC, iv.encode("utf-8"))
    padded_data = pad(data.encode("utf-8"), AES.block_size)
    encrypted_data = cipher.encrypt(padded_data)
    return encrypted_data.hex()  # 使用十六進制，不是 Base64


def aes_decrypt(encrypted_data, key, iv):
    """AES 解密 - 藍新金流專用 Zero Padding 方式"""
    try:
        # 藍新金流使用 Zero Padding，不是 PKCS7
        key_bytes = key.encode('utf-8')[:32].ljust(32, b'\0')
        iv_bytes = iv.encode('utf-8')[:16].ljust(16, b'\0')

        cipher = AES.new(key_bytes, AES.MODE_CBC, iv_bytes)
        decrypted_data = cipher.decrypt(bytes.fromhex(encrypted_data))
        result = decrypted_data.rstrip(b'\0').decode("utf-8")
        logger.error(f"[DEBUG] 藍新金流解密成功：Zero Padding")
        return result
    except Exception as e:
        logger.error(f"[DEBUG] 藍新金流解密失敗：{e}")
        raise ValueError(f"藍新金流解密失敗 - {e}")


def generate_sha256(data):
    """生成 SHA256"""
    return hashlib.sha256(data.encode("utf-8")).hexdigest().upper()
